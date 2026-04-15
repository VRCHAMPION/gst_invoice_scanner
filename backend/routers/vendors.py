"""
vendors.py - Vendor management endpoints
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import get_current_user
from database import get_db
from models import Invoice, User, Vendor
from schemas import VendorOut, VendorDetailOut


def _get_authorized_vendor(vendor_id: str, current_user: User, db: Session) -> Vendor:
    """Parse UUID, fetch vendor, and verify company ownership."""
    try:
        vendor_uuid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_uuid).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if str(vendor.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return vendor


def _get_vendor_stats(vendor_gstin: str, company_id, db: Session) -> dict:
    results = db.query(
        Invoice.status, 
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.total).label("total")
    ).filter(
        Invoice.company_id == company_id,
        Invoice.seller_gstin == vendor_gstin,
    ).group_by(Invoice.status).all()

    total_count = sum(r.count for r in results)
    total_amount = sum((r.total or 0.0) for r in results if r.status == "APPROVED")
    
    if total_count == 0:
        return {"score": None, "label": "New", "total_invoices": 0, "total_amount": 0.0, "approved_count": 0, "pending_count": 0}

    status_map = {r.status: r.count for r in results}
    failed = status_map.get("FAILED", 0)
    rejected = status_map.get("REJECTED", 0)
    pending = status_map.get("PENDING_REVIEW", 0)
    approved = status_map.get("APPROVED", 0)

    score = 100
    if total_count > 0:
        score -= (failed / total_count) * 60
        score -= ((rejected + pending) / total_count) * 30

    score = max(0, int(score))

    if score >= 80:
        label = "Trusted"
    elif score >= 60:
        label = "Caution"
    else:
        label = "Red Flag"

    return {
        "score": score,
        "label": label,
        "total_invoices": approved, # maintain legacy behavior: vendors list shows approved count
        "total_amount": float(total_amount),
        "approved_count": approved,
        "pending_count": pending
    }


router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.get("", response_model=List[VendorOut])
async def get_vendors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of all vendors for the company."""
    if not current_user.company_id:
        return []
    
    # Recalculate vendor stats from approved invoices
    vendors = db.query(Vendor).filter(Vendor.company_id == current_user.company_id).all()
    
    for vendor in vendors:
        stats = _get_vendor_stats(vendor.gstin, current_user.company_id, db)
        vendor.total_invoices = stats["total_invoices"]
        vendor.total_amount = stats["total_amount"]
        vendor.trust_score = stats["score"]
        vendor.trust_label = stats["label"]
    
    db.commit()
    
    return [VendorOut.model_validate(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorDetailOut)
async def get_vendor_detail(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed vendor information."""
    vendor = _get_authorized_vendor(vendor_id, current_user, db)

    stats = _get_vendor_stats(vendor.gstin, current_user.company_id, db)

    return VendorDetailOut(
        id=vendor.id,
        gstin=vendor.gstin,
        name=vendor.name,
        total_invoices=stats["total_invoices"],
        total_amount=stats["total_amount"],
        approved_invoices=stats["approved_count"],
        pending_invoices=stats["pending_count"],
        trust_score=stats["score"],
        trust_label=stats["label"],
    )


@router.get("/{vendor_id}/invoices")
async def get_vendor_invoices(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all invoices for a specific vendor."""
    vendor = _get_authorized_vendor(vendor_id, current_user, db)

    invoices = db.query(Invoice).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.seller_gstin == vendor.gstin
    ).order_by(Invoice.created_at.desc()).all()

    return {
        "vendor": VendorOut.model_validate(vendor),
        "invoices": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "total": inv.total,
                "status": inv.status,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ]
    }
