import uuid
import datetime

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey,
    JSON, CheckConstraint, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

# Indian GSTIN regex: 2 digits + 5 uppercase + 4 digits + 1 letter + 1 alphanum + Z + 1 alphanum
_GSTIN_RE = r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    name          = Column(String)
    role          = Column(String, nullable=False)  # 'owner' | 'employee'
    company_id    = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

    company          = relationship("Company", back_populates="users", foreign_keys=[company_id])
    uploaded_invoices = relationship("Invoice", back_populates="uploader", foreign_keys="Invoice.uploaded_by")

    __table_args__ = (
        CheckConstraint("role IN ('owner', 'employee')", name="ck_users_role"),
        CheckConstraint(
            text(r"email ~ '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$'"),
            name="ck_users_email_format",
        ),
    )


class Company(Base):
    __tablename__ = "companies"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String, unique=True, nullable=False)
    gstin       = Column(String, nullable=False)
    owner_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    webhook_url = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

    users    = relationship("User", back_populates="company", foreign_keys=[User.company_id])
    owner    = relationship("User", foreign_keys=[owner_id])
    invoices = relationship("Invoice", back_populates="company")

    __table_args__ = (
        CheckConstraint(
            text(rf"gstin ~ '{_GSTIN_RE}'"),
            name="ck_companies_gstin_format",
        ),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id           = Column(String, unique=True, index=True, nullable=True)
    company_id       = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    uploaded_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    invoice_number   = Column(String, index=True)
    invoice_date     = Column(String)
    seller_name      = Column(String, index=True)
    seller_gstin     = Column(String, index=True)
    buyer_name       = Column(String)
    buyer_gstin      = Column(String)

    subtotal         = Column(Float)
    cgst             = Column(Float)
    sgst             = Column(Float)
    igst             = Column(Float)
    total            = Column(Float)

    status           = Column(String, default="PROCESSING")
    approval_status  = Column(String, nullable=True)
    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    is_duplicate     = Column(String, nullable=True)
    manually_verified = Column(String, nullable=True)

    error_message    = Column(String, nullable=True)
    raw_json         = Column(JSON)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company  = relationship("Company", back_populates="invoices")
    uploader = relationship("User", back_populates="uploaded_invoices", foreign_keys=[uploaded_by])
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_invoices_company_status",         "company_id", "status"),
        Index("ix_invoices_company_created",         "company_id", "created_at"),
        Index("ix_invoices_company_invoice_number",  "company_id", "invoice_number"),
        CheckConstraint(
            "status IN ('PROCESSING','PENDING_REVIEW','APPROVED','REJECTED','FAILED')",
            name="ck_invoice_status",
        ),
        CheckConstraint(
            "approval_status IS NULL OR approval_status IN ('approved','rejected')",
            name="ck_invoice_approval_status",
        ),
        CheckConstraint(
            "total IS NULL OR total >= 0",
            name="ck_invoice_total_non_negative",
        ),
    )


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status     = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user    = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','rejected')",
            name="ck_join_request_status",
        ),
    )


class Vendor(Base):
    __tablename__ = "vendors"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id     = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    gstin          = Column(String, nullable=False)
    name           = Column(String, nullable=False)
    total_invoices = Column(Float, default=0)
    total_amount   = Column(Float, default=0.0)
    created_at     = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company = relationship("Company")

    __table_args__ = (
        Index("ix_vendors_company_gstin", "company_id", "gstin", unique=True),
        CheckConstraint(
            text(rf"gstin ~ '{_GSTIN_RE}'"),
            name="ck_vendors_gstin_format",
        ),
    )
