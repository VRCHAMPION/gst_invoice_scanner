import csv
import io
import uuid
from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import asyncio
import concurrent.futures

# Executor with 1 worker to prevent OOM / CPU starvation on the free tier
ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

from auth import get_current_user
from database import get_db
from models import Invoice, User, Vendor
from schemas import (
    ExportRequest,
    InvoiceListItem,
    MessageResponse,
    PaginatedInvoices,
    ScanJobResponse,
    ScanStatusResponse,
)
from services.invoice_service import process_invoice_background, trigger_webhook
from validator import calculate_health_score
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_authorized_invoice(invoice_id: str, current_user: User, db: Session) -> Invoice:
    """Parse UUID, fetch invoice, and verify company ownership. Raises HTTPException on failure."""
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")

    invoice = db.query(Invoice).filter(Invoice.id == invoice_uuid).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if str(invoice.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return invoice


class InvoiceUpdateRequest(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    seller_name: Optional[str] = None
    seller_gstin: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total: Optional[float] = None


class ManualInvoiceRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: str = Field(min_length=1)
    seller_name: str = Field(min_length=1, max_length=200)
    seller_gstin: Optional[str] = Field(default=None, max_length=15)
    buyer_name: Optional[str] = Field(default=None, max_length=200)
    buyer_gstin: Optional[str] = Field(default=None, max_length=15)
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total: float = Field(gt=0)


limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api", tags=["invoices"])


class DuplicateCheckRequest(BaseModel):
    invoice_number: str = Field(min_length=1)
    seller_gstin: Optional[str] = None


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    original_invoice_id: Optional[str] = None
    original_upload_date: Optional[str] = None
    original_uploader: Optional[str] = None
    message: Optional[str] = None


@router.post("/invoices/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate_invoice(
    req: DuplicateCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if an invoice with the same number and seller GSTIN already exists."""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Please associate with a company first")

    query = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.invoice_number == req.invoice_number,
        Invoice.status != "FAILED",
    )

    if req.seller_gstin:
        query = query.filter(Invoice.seller_gstin == req.seller_gstin.upper().strip())

    existing = query.first()

    if not existing:
        return DuplicateCheckResponse(is_duplicate=False)

    uploader = db.query(User).filter(User.id == existing.uploaded_by).first()
    uploader_name = uploader.name if uploader else "Unknown"

    return DuplicateCheckResponse(
        is_duplicate=True,
        original_invoice_id=str(existing.id),
        original_upload_date=existing.created_at.strftime("%Y-%m-%d %H:%M") if existing.created_at else None,
        original_uploader=uploader_name,
        message=(
            f"Invoice #{req.invoice_number} from this seller was already uploaded "
            f"on {existing.created_at.strftime('%Y-%m-%d')} by {uploader_name}."
        ),
    )


@router.post("/scan", response_model=ScanJobResponse)
@limiter.limit("10/minute")
async def scan_invoice(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Please associate with a company first")

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    job_id = str(uuid.uuid4())

    placeholder = Invoice(
        job_id=job_id,
        company_id=current_user.company_id,
        uploaded_by=current_user.id,
        status="PROCESSING",
        raw_json={},
    )
    db.add(placeholder)
    db.commit()

    async def run_ocr_safe():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            ocr_executor,
            process_invoice_background,
            job_id, contents, file.content_type,
            current_user.id, current_user.company_id
        )

    background_tasks.add_task(run_ocr_safe)
    return ScanJobResponse(job_id=job_id, status="processing")


@router.get("/scan/status/{job_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check invoice processing status."""
    invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(invoice.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if invoice.status == "PROCESSING":
        return ScanStatusResponse(status="processing")

    if invoice.status == "FAILED":
        return ScanStatusResponse(
            status="failed",
            error=invoice.error_message or "Extraction failed",
            id=str(invoice.id),
            **{
                "is_duplicate": invoice.is_duplicate,
                "error_message": invoice.error_message,
            },
        )

    data = dict(invoice.raw_json or {})
    data["id"] = str(invoice.id)
    data["status"] = invoice.status
    data["is_duplicate"] = invoice.is_duplicate
    data["health_score"] = calculate_health_score(data)
    return ScanStatusResponse(**data)


@router.get("/invoices", response_model=PaginatedInvoices)
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 50,
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vendor: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
):
    """Get paginated invoice list with search and filters."""
    if not current_user.company_id:
        return PaginatedInvoices(items=[], total=0, page=page, pages=0)

    limit = min(limit, 200)
    page = max(page, 1)
    offset = (page - 1) * limit

    base = db.query(Invoice).filter(Invoice.company_id == current_user.company_id)

    if q:
        search_term = f"%{q}%"
        base = base.filter(
            (Invoice.invoice_number.ilike(search_term)) |
            (Invoice.seller_name.ilike(search_term)) |
            (Invoice.buyer_name.ilike(search_term)) |
            (Invoice.seller_gstin.ilike(search_term)) |
            (Invoice.buyer_gstin.ilike(search_term))
        )

    if status:
        base = base.filter(Invoice.status == status.upper())

    if date_from:
        base = base.filter(Invoice.invoice_date >= date_from)
    if date_to:
        base = base.filter(Invoice.invoice_date <= date_to)

    if vendor:
        base = base.filter(Invoice.seller_gstin == vendor.upper())

    if amount_min is not None:
        base = base.filter(Invoice.total >= amount_min)
    if amount_max is not None:
        base = base.filter(Invoice.total <= amount_max)

    total = base.count()
    invoices = base.order_by(Invoice.created_at.desc()).offset(offset).limit(limit).all()

    return PaginatedInvoices(
        items=[InvoiceListItem.model_validate(inv) for inv in invoices],
        total=total,
        page=page,
        pages=ceil(total / limit) if total > 0 else 0,
    )


@router.post("/invoices/manual", response_model=MessageResponse)
async def create_manual_invoice(
    req: ManualInvoiceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an invoice record from manually entered data, bypassing OCR."""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Please associate with a company first")

    
    existing = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.invoice_number == req.invoice_number,
        Invoice.status != "FAILED",
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Invoice {req.invoice_number} already exists (uploaded on {existing.created_at.strftime('%Y-%m-%d')})",
        )

    raw = {
        "invoice_number": req.invoice_number,
        "invoice_date": req.invoice_date,
        "seller_name": req.seller_name,
        "seller_gstin": req.seller_gstin,
        "buyer_name": req.buyer_name,
        "buyer_gstin": req.buyer_gstin,
        "subtotal": req.subtotal,
        "cgst": req.cgst,
        "sgst": req.sgst,
        "igst": req.igst,
        "total": req.total,
        "items": [],
        "manual_entry": True,
    }

    invoice = Invoice(
        job_id=str(uuid.uuid4()),
        company_id=current_user.company_id,
        uploaded_by=current_user.id,
        invoice_number=req.invoice_number,
        invoice_date=req.invoice_date,
        seller_name=req.seller_name,
        seller_gstin=req.seller_gstin.upper() if req.seller_gstin else None,
        buyer_name=req.buyer_name,
        buyer_gstin=req.buyer_gstin.upper() if req.buyer_gstin else None,
        subtotal=req.subtotal,
        cgst=req.cgst,
        sgst=req.sgst,
        igst=req.igst,
        total=req.total,
        status="PENDING_REVIEW",
        manually_verified="true",
        raw_json=raw,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    if req.seller_gstin and req.seller_name:
        from services.invoice_service import _create_or_update_vendor
        _create_or_update_vendor(db, current_user.company_id, req.seller_gstin, req.seller_name)

    return MessageResponse(message=str(invoice.id))


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single invoice by ID."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)

    data = dict(invoice.raw_json or {})
    data["id"] = str(invoice.id)
    data["status"] = invoice.status
    data["is_duplicate"] = invoice.is_duplicate
    data["error_message"] = invoice.error_message
    data["invoice_number"] = invoice.invoice_number
    data["invoice_date"] = invoice.invoice_date
    data["seller_name"] = invoice.seller_name
    data["seller_gstin"] = invoice.seller_gstin
    data["buyer_name"] = invoice.buyer_name
    data["buyer_gstin"] = invoice.buyer_gstin
    data["subtotal"] = invoice.subtotal
    data["cgst"] = invoice.cgst
    data["sgst"] = invoice.sgst
    data["igst"] = invoice.igst
    data["total"] = invoice.total
    data["health_score"] = calculate_health_score(data)
    return data


@router.patch("/invoices/{invoice_id}", response_model=MessageResponse)
async def update_invoice(
    invoice_id: str,
    req: InvoiceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update extracted invoice data (edit mode corrections)."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)

    if invoice.status not in ("PENDING_REVIEW", "FAILED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit invoice with status: {invoice.status}. Only PENDING_REVIEW or FAILED invoices can be edited.",
        )

    update_data = req.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(invoice, field_name, value)

    raw = dict(invoice.raw_json or {})
    raw.update(update_data)
    invoice.raw_json = raw
    invoice.manually_verified = "true"

    db.commit()
    return MessageResponse(message="Invoice updated successfully")


@router.post("/invoices/{invoice_id}/retry", response_model=MessageResponse)
async def retry_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a FAILED invoice record so the user can re-upload."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)

    if invoice.status != "FAILED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry invoice with status: {invoice.status}. Only FAILED invoices can be retried.",
        )

    db.delete(invoice)
    db.commit()
    return MessageResponse(message="Failed invoice removed. Please re-upload the file to reprocess it.")


@router.post("/export")
async def export_invoice(
    req: ExportRequest,
    current_user: User = Depends(get_current_user),
):
    """Export invoice data as CSV."""
    health = req.health_score or {}
    health_score_val = health.get("score", "N/A") if isinstance(health, dict) else "N/A"

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "invoice_number", "vendor_name", "date",
        "total_amount", "cgst", "sgst", "igst",
        "status", "health_score",
    ])

    writer.writerow([
        req.invoice_number or "",
        req.seller_name or "",
        req.invoice_date or "",
        req.total or 0,
        req.cgst or 0,
        req.sgst or 0,
        req.igst or 0,
        req.status or "",
        health_score_val,
    ])

    output.seek(0)
    filename = f"invoice_{req.invoice_number or 'export'}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/invoices/{invoice_id}/approve", response_model=MessageResponse)
async def approve_invoice(
    invoice_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a pending invoice."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)

    if invoice.status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve invoice with status: {invoice.status}. Only PENDING_REVIEW invoices can be approved.",
        )

    invoice.status = "APPROVED"
    invoice.approval_status = "approved"
    invoice.approved_by = current_user.id
    invoice.approved_at = datetime.utcnow()

    if invoice.seller_gstin:
        vendor = db.query(Vendor).filter(
            Vendor.company_id == current_user.company_id,
            Vendor.gstin == invoice.seller_gstin.upper()
        ).first()
        if vendor:
            vendor.total_invoices += 1
            vendor.total_amount += (invoice.total or 0.0)

    from models import Company
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if company and company.webhook_url:
        payload = dict(invoice.raw_json or {})
        payload["id"] = str(invoice.id)
        payload["status"] = "APPROVED"
        background_tasks.add_task(trigger_webhook, company.webhook_url, payload)

    db.commit()
    return MessageResponse(message=f"Invoice {invoice.invoice_number or invoice_id} approved successfully")


@router.post("/invoices/{invoice_id}/reject", response_model=MessageResponse)
async def reject_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject and delete a pending invoice."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)

    if invoice.status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject invoice with status: {invoice.status}. Only PENDING_REVIEW invoices can be rejected.",
        )

    db.delete(invoice)
    db.commit()
    return MessageResponse(message=f"Invoice {invoice.invoice_number or invoice_id} rejected and deleted successfully")

@router.delete("/invoices/{invoice_id}", response_model=MessageResponse)
async def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an invoice completely from history."""
    invoice = _get_authorized_invoice(invoice_id, current_user, db)
    db.delete(invoice)
    db.commit()
    return MessageResponse(message=f"Invoice {invoice_id} deleted successfully")

