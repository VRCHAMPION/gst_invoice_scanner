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
from pydantic import BaseModel


class VendorOut(BaseModel):
    id: uuid.UUID
    gstin: str
    name: str
    total_invoices: int
    total_amount: float
    
    model_config = {"from_attributes": True}


class VendorDetailOut(BaseModel):
    id: uuid.UUID
    gstin: str
    name: str
    total_invoices: int
    total_amount: float
    approved_invoices: int
    pending_invoices: int
    
    model_config = {"from_attributes": True}


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
    
    db.commit()
    
    return [VendorOut.model_validate(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorDetailOut)
async def get_vendor_detail(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed vendor information."""
    try:
        vendor_uuid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_uuid).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if str(vendor.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get detailed stats
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
    
    return VendorDetailOut(
        id=str(vendor.id),
        gstin=vendor.gstin,
        name=vendor.name,
        total_invoices=approved.count or 0,
        total_amount=float(approved.total or 0.0),
        approved_invoices=approved.count or 0,
        pending_invoices=pending or 0,
    )


@router.get("/{vendor_id}/invoices")
async def get_vendor_invoices(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all invoices for a specific vendor."""
    try:
        vendor_uuid = uuid.UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_uuid).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    if str(vendor.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
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
