from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    role = Column(String, nullable=False) # 'owner' or 'employee'
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="users", foreign_keys=[company_id])
    uploaded_invoices = relationship("Invoice", back_populates="uploader")

    __table_args__ = (
        CheckConstraint(role.in_(['owner', 'employee']), name='valid_role'),
    )

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    gstin = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="company", foreign_keys=[User.company_id])
    owner = relationship("User", foreign_keys=[owner_id])
    invoices = relationship("Invoice", back_populates="company")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, unique=True, index=True, nullable=True)  # set on upload, used for status polling
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    invoice_number = Column(String)
    invoice_date = Column(String)
    seller_name = Column(String)
    seller_gstin = Column(String)
    buyer_name = Column(String)
    buyer_gstin = Column(String)
    
    subtotal = Column(Float)
    cgst = Column(Float)
    sgst = Column(Float)
    igst = Column(Float)
    total = Column(Float)
    
    status = Column(String, default="PROCESSING")
    error_message = Column(String, nullable=True)
    
    raw_json = Column(JSON) # JSONB in Postgres
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="invoices")
    uploader = relationship("User", back_populates="uploaded_invoices")

class JoinRequest(Base):
    __tablename__ = "join_requests"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    status     = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user    = relationship("User", foreign_keys=[user_id])
    company = relationship("Company", foreign_keys=[company_id])
