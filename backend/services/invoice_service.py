"""
invoice_service.py — Background invoice processing logic.
Isolated here so it can be tested independently and later moved to Celery.
"""
import uuid
import structlog

from parser import extract_invoice_data

log = structlog.get_logger()


def process_invoice_background(
    job_id: str,
    file_bytes: bytes,
    content_type: str,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
) -> None:
    """
    Run OCR + LLM extraction and persist the result to the DB.
    Called via FastAPI BackgroundTasks — runs in a thread pool worker.

    NOTE: We open a fresh SessionLocal here (not the request-scoped session)
    because BackgroundTasks run after the request session is closed.
    This is intentional and worker-safe across multiple Gunicorn processes.
    """
    from database import SessionLocal
    from models import Invoice

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
        invoice.status         = "SUCCESS"
        invoice.raw_json       = data
        db.commit()
        db.refresh(invoice)
        log.info("invoice_processed", job_id=job_id)

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
            pass  # DB itself may be unavailable — nothing more we can do
    finally:
        db.close()
