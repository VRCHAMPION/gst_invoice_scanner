"""
schemas.py — All Pydantic request and response models.
Centralised here so routers stay thin and response_model= is always explicit.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from validator import GSTIN_REGEX

# ── Shared validators ─────────────────────────────────────────────────

def _validate_gstin_field(v: str) -> str:
    v = v.strip().upper()
    if len(v) != 15:
        raise ValueError("GSTIN must be exactly 15 characters")
    if not GSTIN_REGEX.match(v):
        raise ValueError("Invalid GSTIN format")
    state_code = int(v[:2])
    if state_code < 1 or state_code > 37:
        raise ValueError(f"Invalid GSTIN state code: {v[:2]}")
    return v


# ══════════════════════════════════════════════════════════════════════
# AUTH — Request models
# ══════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # NOTE: 'role' is intentionally absent — always set server-side to 'owner'.


# ══════════════════════════════════════════════════════════════════════
# AUTH — Response models
# ══════════════════════════════════════════════════════════════════════

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    role: str
    company_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut


class MessageResponse(BaseModel):
    message: str


# ══════════════════════════════════════════════════════════════════════
# COMPANY — Request models
# ══════════════════════════════════════════════════════════════════════

class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    gstin: str = Field(min_length=15, max_length=15)

    @field_validator("gstin")
    @classmethod
    def gstin_format(cls, v: str) -> str:
        return _validate_gstin_field(v)


class JoinCompanyRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=100)


class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


# ══════════════════════════════════════════════════════════════════════
# COMPANY — Response models
# ══════════════════════════════════════════════════════════════════════

class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    gstin: str
    owner_id: Optional[uuid.UUID] = None
    employee_count: Optional[int] = None

    model_config = {"from_attributes": True}


class JoinRequestOut(BaseModel):
    id: str
    user_id: str
    name: Optional[str] = None
    email: str
    created_at: str


class JoinRequestStatusResponse(BaseModel):
    status: str
    company_id: Optional[str] = None
    company_name: Optional[str] = None


class InviteResponse(BaseModel):
    message: str
    id: uuid.UUID


# ══════════════════════════════════════════════════════════════════════
# INVOICE — Request models
# ══════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    """Payload sent by the frontend to POST /api/export."""
    invoice_number: Optional[str] = None
    seller_name: Optional[str] = None
    invoice_date: Optional[str] = None
    total: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    status: Optional[str] = None
    health_score: Optional[Dict[str, Any]] = None
    # Allow any extra fields from the scan result payload
    model_config = {"extra": "allow"}


# ══════════════════════════════════════════════════════════════════════
# INVOICE — Response models
# ══════════════════════════════════════════════════════════════════════

class InvoiceListItem(BaseModel):
    """Lightweight invoice schema for list views — excludes raw_json."""
    id: uuid.UUID
    job_id: Optional[str] = None
    company_id: uuid.UUID
    uploaded_by: uuid.UUID
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
    status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedInvoices(BaseModel):
    items: List[InvoiceListItem]
    total: int
    page: int
    pages: int


class ScanJobResponse(BaseModel):
    job_id: str
    status: str


class HealthScoreOut(BaseModel):
    score: int
    grade: str
    status: str
    issues: List[str]
    warnings: List[str]
    passed_checks: List[str]
    summary: str


class ScanStatusResponse(BaseModel):
    status: str
    error: Optional[str] = None
    id: Optional[str] = None
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
    health_score: Optional[HealthScoreOut] = None
    model_config = {"extra": "allow"}


# ══════════════════════════════════════════════════════════════════════
# ANALYTICS — Response models
# ══════════════════════════════════════════════════════════════════════

class MonthlySpend(BaseModel):
    month: str
    total: float
    tax: float


class MonthlyCount(BaseModel):
    month: str
    count: int


class SupplierSpend(BaseModel):
    name: str
    total_spend: float


class AnalyticsResponse(BaseModel):
    total_invoices: int
    total_spend: float
    total_tax: float
    monthly_spend: List[MonthlySpend]
    top_suppliers: List[SupplierSpend]
    monthly_invoice_count: List[MonthlyCount]


class SupplierItc(BaseModel):
    seller_name: str
    seller_gstin: str
    cgst: float
    sgst: float
    igst: float
    total_itc: float


class ItcCurrentMonth(BaseModel):
    total_itc: float


class ItcSummaryResponse(BaseModel):
    current_month: ItcCurrentMonth
    percentage_change: float
    disclaimer: str
    supplier_breakdown: List[SupplierItc]


# ══════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str
    db: str
    version: str


# ══════════════════════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════════════════════

class UserListItem(BaseModel):
    id: str
    name: Optional[str] = None
    email: str
    role: str
