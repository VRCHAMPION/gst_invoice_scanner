import uuid
import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    role = Column(String, nullable=False)  # 'owner' | 'employee'
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="users", foreign_keys=[company_id])
    uploaded_invoices = relationship("Invoice", back_populates="uploader", foreign_keys="Invoice.uploaded_by")

    __table_args__ = (
        CheckConstraint(role.in_(["owner", "employee"]), name="valid_role"),
    )


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    gstin = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="company", foreign_keys=[User.company_id])
    owner = relationship("User", foreign_keys=[owner_id])
    invoices = relationship("Invoice", back_populates="company")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, unique=True, index=True, nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    invoice_number = Column(String, index=True)
    invoice_date = Column(String)
    seller_name = Column(String, index=True)
    seller_gstin = Column(String, index=True)
    buyer_name = Column(String)
    buyer_gstin = Column(String)

    subtotal = Column(Float)
    cgst = Column(Float)
    sgst = Column(Float)
    igst = Column(Float)
    total = Column(Float)

    status = Column(String, default="PROCESSING")  # PROCESSING | PENDING_REVIEW | APPROVED | REJECTED | FAILED
    approval_status = Column(String, nullable=True)  # null | approved | rejected
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    is_duplicate = Column(String, nullable=True)  # null | true (stores original invoice ID if duplicate)
    manually_verified = Column(String, nullable=True)  # null | true
    
    error_message = Column(String, nullable=True)
    raw_json = Column(JSON)  # JSONB in Postgres
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="invoices")
    uploader = relationship("User", back_populates="uploaded_invoices", foreign_keys=[uploaded_by])
    approver = relationship("User", foreign_keys=[approved_by])

    # composite indexes for analytics query performance
    __table_args__ = (
        Index("ix_invoices_company_status", "company_id", "status"),
        Index("ix_invoices_company_created", "company_id", "created_at"),
        Index("ix_invoices_company_invoice_number", "company_id", "invoice_number"),
    )


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    gstin = Column(String, nullable=False)
    name = Column(String, nullable=False)
    total_invoices = Column(Float, default=0)
    total_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company = relationship("Company")

    __table_args__ = (
        Index("ix_vendors_company_gstin", "company_id", "gstin", unique=True),
    )
