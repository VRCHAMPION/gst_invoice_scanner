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


def _calculate_trust_score(vendor_gstin: str, company_id, db: Session) -> tuple:
    counts = db.query(
        Invoice.status, func.count(Invoice.id)
    ).filter(
        Invoice.company_id == company_id,
        Invoice.seller_gstin == vendor_gstin,
    ).group_by(Invoice.status).all()

    total = sum(c[1] for c in counts)
    if total == 0:
        return None, "New"

    status_map = {c[0]: c[1] for c in counts}
    failed = status_map.get("FAILED", 0)
    rejected = status_map.get("REJECTED", 0)
    pending = status_map.get("PENDING_REVIEW", 0)

    score = 100
    if total > 0:
        score -= (failed / total) * 60
        score -= ((rejected + pending) / total) * 30

    score = max(0, int(score))

    if score >= 80:
        label = "Trusted"
    elif score >= 60:
        label = "Caution"
    else:
        label = "Red Flag"

    return score, label


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
        stats = db.query(
            func.count(Invoice.id).label("count"),
            func.sum(Invoice.total).label("total")
        ).filter(
            Invoice.company_id == current_user.company_id,
            Invoice.seller_gstin == vendor.gstin,
            Invoice.status == "APPROVED"
        ).first()
        
        vendor.total_invoices = stats.count or 0
        vendor.total_amount = float(stats.total or 0.0)
        score, label = _calculate_trust_score(vendor.gstin, current_user.company_id, db)
        vendor.trust_score = score
        vendor.trust_label = label
    
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

    approved = db.query(
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.total).label("total")
    ).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.seller_gstin == vendor.gstin,
        Invoice.status == "APPROVED"
    ).first()

    pending = db.query(func.count(Invoice.id)).filter(
        Invoice.company_id == current_user.company_id,
        Invoice.seller_gstin == vendor.gstin,
        Invoice.status == "PENDING_REVIEW"
    ).scalar()

    score, label = _calculate_trust_score(vendor.gstin, current_user.company_id, db)

    return VendorDetailOut(
        id=vendor.id,
        gstin=vendor.gstin,
        name=vendor.name,
        total_invoices=approved.count or 0,
        total_amount=float(approved.total or 0.0),
        approved_invoices=approved.count or 0,
        pending_invoices=pending or 0,
        trust_score=score,
        trust_label=label,
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
