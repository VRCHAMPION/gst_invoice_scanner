import csv
import io
import uuid
from math import ceil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Invoice, User
from schemas import (
    ExportRequest,
    InvoiceListItem,
    MessageResponse,
    PaginatedInvoices,
    ScanJobResponse,
    ScanStatusResponse,
)
from services.invoice_service import process_invoice_background
from validator import calculate_health_score
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api", tags=["invoices"])

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

    # Check file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    job_id = str(uuid.uuid4())

    # Create placeholder record
    placeholder = Invoice(
        job_id=job_id,
        company_id=current_user.company_id,
        uploaded_by=current_user.id,
        status="PROCESSING",
        raw_json={},
    )
    db.add(placeholder)
    db.commit()

    # Process in background
    background_tasks.add_task(
        process_invoice_background,
        job_id, contents, file.content_type,
        current_user.id, current_user.company_id,
    )
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
        )

    # Success - return full data with health score
    data = invoice.raw_json or {}
    data["id"] = str(invoice.id)
    data["status"] = "completed"
    data["health_score"] = calculate_health_score(data)
    return ScanStatusResponse(**data)


@router.get("/invoices", response_model=PaginatedInvoices)
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 50,
    q: Optional[str] = None,  # Search query
    status: Optional[str] = None,  # Filter by status
    date_from: Optional[str] = None,  # Filter by date range
    date_to: Optional[str] = None,
    vendor: Optional[str] = None,  # Filter by seller_gstin
    amount_min: Optional[float] = None,  # Filter by amount range
    amount_max: Optional[float] = None,
):
    """Get paginated invoice list with search and filters."""
    if not current_user.company_id:
        return PaginatedInvoices(items=[], total=0, page=page, pages=0)

    limit = min(limit, 200)
    page = max(page, 1)
    offset = (page - 1) * limit

    # Base query
    base = db.query(Invoice).filter(Invoice.company_id == current_user.company_id)
    
    # Apply search
    if q:
        search_term = f"%{q}%"
        base = base.filter(
            (Invoice.invoice_number.ilike(search_term)) |
            (Invoice.seller_name.ilike(search_term)) |
            (Invoice.buyer_name.ilike(search_term)) |
            (Invoice.seller_gstin.ilike(search_term)) |
            (Invoice.buyer_gstin.ilike(search_term))
        )
    
    # Apply status filter
    if status:
        base = base.filter(Invoice.status == status.upper())
    
    # Apply date range filter
    if date_from:
        base = base.filter(Invoice.invoice_date >= date_from)
    if date_to:
        base = base.filter(Invoice.invoice_date <= date_to)
    
    # Apply vendor filter
    if vendor:
        base = base.filter(Invoice.seller_gstin == vendor.upper())
    
    # Apply amount range filter
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a pending invoice."""
    from datetime import datetime
    from models import Vendor
    
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_uuid).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if str(invoice.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if invoice.status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve invoice with status: {invoice.status}. Only PENDING_REVIEW invoices can be approved."
        )
    
    invoice.status = "APPROVED"
    invoice.approval_status = "approved"
    invoice.approved_by = current_user.id
    invoice.approved_at = datetime.utcnow()
    
    # Update vendor stats
    if invoice.seller_gstin:
        vendor = db.query(Vendor).filter(
            Vendor.company_id == current_user.company_id,
            Vendor.gstin == invoice.seller_gstin.upper()
        ).first()
        
        if vendor:
            vendor.total_invoices += 1
            vendor.total_amount += (invoice.total or 0.0)
    
    db.commit()
    
    return MessageResponse(message=f"Invoice {invoice.invoice_number or invoice_id} approved successfully")


@router.post("/invoices/{invoice_id}/reject", response_model=MessageResponse)
async def reject_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a pending invoice."""
    from datetime import datetime
    
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_uuid).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if str(invoice.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if invoice.status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot reject invoice with status: {invoice.status}. Only PENDING_REVIEW invoices can be rejected."
        )
    
    invoice.status = "REJECTED"
    invoice.approval_status = "rejected"
    invoice.approved_by = current_user.id
    invoice.approved_at = datetime.utcnow()
    db.commit()
    
    return MessageResponse(message=f"Invoice {invoice.invoice_number or invoice_id} rejected successfully")
