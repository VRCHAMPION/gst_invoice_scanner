"""
invoice_service.py - Background invoice processing
TODO: migrate to Celery when we need better scalability
"""
import uuid
import structlog

import httpx

from parser import extract_invoice_data

log = structlog.get_logger()


async def trigger_webhook(webhook_url: str, payload: dict) -> None:
    """Fire and forget webhook payload delivery."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            if response.status_code >= 400:
                log.warning("webhook_error_response", url=webhook_url, status_code=response.status_code, response=response.text[:200])
            else:
                log.info("webhook_triggered", url=webhook_url, status_code=response.status_code)
    except Exception as e:
        log.error("webhook_failed", url=webhook_url, error=str(e))


def _create_or_update_vendor(db, company_id: uuid.UUID, seller_gstin: str, seller_name: str) -> None:
    """Create or update vendor record from invoice data."""
    from models import Vendor
    
    if not seller_gstin or not seller_name:
        return
    
    seller_gstin = seller_gstin.upper().strip()
    
    # Check if vendor exists
    vendor = db.query(Vendor).filter(
        Vendor.company_id == company_id,
        Vendor.gstin == seller_gstin
    ).first()
    
    if vendor:
        # Update existing vendor name if it changed
        if vendor.name != seller_name:
            vendor.name = seller_name
            db.commit()
    else:
        # Create new vendor
        vendor = Vendor(
            company_id=company_id,
            gstin=seller_gstin,
            name=seller_name,
            total_invoices=0,
            total_amount=0.0
        )
        db.add(vendor)
        db.commit()
        log.info("vendor_created", gstin=seller_gstin, name=seller_name)


def process_invoice_background(
    job_id: str,
    file_bytes: bytes,
    content_type: str,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
) -> None:
    """
    Process invoice in background thread.
    Opens fresh DB session since BackgroundTasks run after request closes.
    """
    from database import SessionLocal
    from models import Invoice, Company, User

    db = SessionLocal()
    try:
        data = extract_invoice_data(file_bytes, content_type)

        invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
        if not invoice:
            log.warning("invoice_record_missing", job_id=job_id)
            return

        if data.get("status") == "failed":
            invoice.status = "FAILED"
            invoice.error_message = data.get("error", "Unknown extraction failure")
            invoice.raw_json = data
            db.commit()
            return

        # Get company GSTIN for validation
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            invoice.status = "FAILED"
            invoice.error_message = "Company not found"
            invoice.raw_json = data
            db.commit()
            return

        company_gstin = company.gstin.upper() if company.gstin else None
        seller_gstin = (data.get("seller_gstin") or "").upper()
        buyer_gstin = (data.get("buyer_gstin") or "").upper()

        # Validate that either seller or buyer GSTIN matches company GSTIN
        if company_gstin:
            if seller_gstin != company_gstin and buyer_gstin != company_gstin:
                log.warning("invoice_gstin_mismatch", job_id=job_id, company_gstin=company_gstin,
                           seller_gstin=seller_gstin, buyer_gstin=buyer_gstin)
                invoice.status = "FAILED"
                invoice.error_message = f"GSTIN Mismatch: Invoice GSTIN does not match Company GSTIN ({company_gstin})"
                invoice.raw_json = data
                db.commit()
                return

        # Check for duplicate invoice (by Invoice Number + Seller GSTIN)
        invoice_number = data.get("invoice_number")
        data_seller_gstin = (data.get("seller_gstin") or "").upper().strip()
        if invoice_number:
            dup_query = db.query(Invoice).filter(
                Invoice.company_id == company_id,
                Invoice.invoice_number == invoice_number,
                Invoice.status != "FAILED",
                Invoice.id != invoice.id
            )
            # If seller GSTIN is available, use composite key for stronger match
            if data_seller_gstin:
                dup_query = dup_query.filter(Invoice.seller_gstin == data_seller_gstin)

            existing = dup_query.first()
            
            if existing:
                invoice.status = "FAILED"
                invoice.is_duplicate = str(existing.id)
                uploader_name = db.query(User).filter(User.id == existing.uploaded_by).first()
                uploader_str = uploader_name.name if uploader_name else "Unknown"
                invoice.invoice_number = invoice_number
                invoice.seller_gstin = data_seller_gstin or None
                invoice.seller_name = data.get("seller_name")
                invoice.error_message = (
                    f"Duplicate invoice: #{invoice_number} from seller "
                    f"{data.get('seller_name') or data_seller_gstin or 'Unknown'} "
                    f"was already uploaded on "
                    f"{existing.created_at.strftime('%Y-%m-%d %H:%M')} by {uploader_str}"
                )
                invoice.raw_json = data
                db.commit()
                log.warning("invoice_duplicate", job_id=job_id, invoice_number=invoice_number,
                           seller_gstin=data_seller_gstin, original_id=str(existing.id))
                return

        invoice.invoice_number = data.get("invoice_number")
        invoice.invoice_date   = data.get("invoice_date")
        invoice.seller_name    = data.get("seller_name")
        invoice.seller_gstin   = data.get("seller_gstin")
        invoice.buyer_name     = data.get("buyer_name")
        invoice.buyer_gstin    = data.get("buyer_gstin")
        invoice.subtotal       = data.get("subtotal")
        invoice.cgst           = data.get("cgst")
        invoice.sgst           = data.get("sgst")
        invoice.igst           = data.get("igst")
        invoice.total          = data.get("total")
        invoice.status         = "PENDING_REVIEW"  # Changed from SUCCESS to PENDING_REVIEW
        invoice.raw_json       = data
        db.commit()
        db.refresh(invoice)
        
        # Auto-create or update vendor
        _create_or_update_vendor(db, company_id, data.get("seller_gstin"), data.get("seller_name"))
        
        log.info("invoice_processed", job_id=job_id, status="pending_review")

    except Exception as e:
        log.error("invoice_processing_failed", job_id=job_id, error=str(e))
        try:
            invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
            if invoice:
                invoice.status = "FAILED"
                invoice.error_message = str(e)
                invoice.raw_json = {"error": str(e)}
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
