import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from parser import extract_invoice_data
from database import get_db, init_db
from models import User, Company, Invoice
from validator import calculate_health_score
from auth import (
    get_current_user, hash_password, verify_password,
    create_access_token, LoginRequest, RegisterRequest, RoleChecker
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import openpyxl
import io
from pydantic import BaseModel

# ── App Setup ─────────────────────────────────────────────────────────
app = FastAPI(title="GST Invoice Scanner Enterprise API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# ── Request Models ────────────────────────────────────────────────────
class CompanyCreate(BaseModel):
    name: str
    gstin: str

class InviteUserRequest(BaseModel):
    email: str
    name: str
    password: str # For simplicity in MVP, usually an invite link/token is sent

# ── Auth Routes (PUBLIC) ──────────────────────────────────────────────
@app.post("/api/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={
        "sub": str(user.id), 
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id, 
            "email": user.email, 
            "name": user.name, 
            "role": user.role,
            "company_id": user.company_id
        }
    }

@app.post("/api/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # New user defaults to no company and no role (or first role they take)
    # Actually, let's default to 'owner' if they are the one creating a company later
    # OR create a temporary state. Let's say role is 'owner' by default for new registers.
    hashed = hash_password(req.password)
    new_user = User(
        name=req.name, 
        email=req.email, 
        password_hash=hashed, 
        role=req.role or 'owner'
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": new_user.id, "email": new_user.email, "role": new_user.role}
    }

# ── Company Management ────────────────────────────────────────────────
@app.post("/api/companies")
async def create_company(
    req: CompanyCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.company_id:
        raise HTTPException(status_code=400, detail="User already belongs to a company")
    
    # Check GSTIN
    existing = db.query(Company).filter(Company.gstin == req.gstin).first()
    if existing:
        raise HTTPException(status_code=400, detail="GSTIN already registered")

    company = Company(
        name=req.name,
        gstin=req.gstin,
        owner_id=current_user.id
    )
    db.add(company)
    db.flush() # Get company ID without committing yet
    
    current_user.company_id = company.id
    current_user.role = 'owner'
    
    db.commit()
    db.refresh(company)
    return company

@app.get("/api/companies")
async def get_my_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        return []
    
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        return []

    # Add employee count if owner
    emp_count = db.query(User).filter(User.company_id == company.id).count()
    
    return [{
        "id": company.id,
        "name": company.name,
        "gstin": company.gstin,
        "owner_id": company.owner_id,
        "employee_count": emp_count
    }]

class JoinCompanyRequest(BaseModel):
    company_name: str

@app.post("/api/companies/join")
async def join_company(
    req: JoinCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.company_id:
        raise HTTPException(status_code=400, detail="User already linked to a company")
    
    company = db.query(Company).filter(Company.name == req.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found. Please check the name exactly.")
    
    current_user.company_id = company.id
    current_user.role = "employee" # Force employee role when joining
    db.commit()
    return {"message": "Successfully joined company", "company": company.name}

@app.post("/api/invite-user")
async def invite_user(
    req: InviteUserRequest,
    current_user: User = Depends(RoleChecker(['owner'])),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered")
    
    new_employee = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role='employee',
        company_id=current_user.company_id
    )
    db.add(new_employee)
    db.commit()
    return {"message": "User invited and added to company", "id": new_employee.id}

@app.get("/api/users")
async def list_company_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not part of a company")
    
    return db.query(User).filter(User.company_id == current_user.company_id).all()

# ── Scan & Processing ─────────────────────────────────────────────────
scan_jobs = {}

def process_invoice_background(job_id: str, file_bytes: bytes, content_type: str, user_id: uuid.UUID, company_id: uuid.UUID):
    from database import SessionLocal
    db = SessionLocal()
    try:
        data = extract_invoice_data(file_bytes, content_type)
        if data.get("status") == "failed":
            scan_jobs[job_id] = data
            return
            
        new_invoice = Invoice(
            user_id=user_id, # This field is 'uploaded_by' in models.py, fixing below
            company_id=company_id,
            uploaded_by=user_id,
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            seller_name=data.get("seller_name"),
            seller_gstin=data.get("seller_gstin"),
            buyer_name=data.get("buyer_name"),
            buyer_gstin=data.get("buyer_gstin"),
            subtotal=data.get("subtotal"),
            cgst=data.get("cgst"),
            sgst=data.get("sgst"),
            igst=data.get("igst"),
            total=data.get("total"),
            raw_json=data
        )
        db.add(new_invoice)
        db.commit()
        
        data["id"] = str(new_invoice.id)
        data["health_score"] = calculate_health_score(data)
        data["status"] = "completed"
        scan_jobs[job_id] = data
    except Exception as e:
        scan_jobs[job_id] = {"status": "failed", "error": str(e)}
    finally:
        db.close()

@app.post("/scan")
async def scan_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Please associate with a company first")

    contents = await file.read()
    job_id = str(uuid.uuid4())
    scan_jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(
        process_invoice_background, 
        job_id, contents, file.content_type, current_user.id, current_user.company_id
    )
    return {"job_id": job_id, "status": "processing"}

@app.get("/scan/status/{job_id}")
async def get_scan_status(job_id: str):
    if job_id not in scan_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return scan_jobs[job_id]

@app.get("/api/invoices")
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        return []
        
    return db.query(Invoice).filter(Invoice.company_id == current_user.company_id).order_by(Invoice.created_at.desc()).all()

@app.get("/api/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        return {}
    
    invoices = db.query(Invoice).filter(Invoice.company_id == current_user.company_id).all()
    
    total_spend = sum(inv.total for inv in invoices if inv.total)
    total_tax = sum((inv.cgst or 0) + (inv.sgst or 0) + (inv.igst or 0) for inv in invoices)
    
    # Simple monthly aggregation
    monthly_spend = []
    # (Mock logic for now or simple grouping)
    
    return {
        "total_invoices": len(invoices),
        "total_spend": total_spend,
        "total_tax": total_tax,
        "monthly_spend": [],
        "top_suppliers": [],
        "monthly_invoice_count": []
    }

@app.get("/api/itc-summary")
async def get_itc_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        return {}
    
    return {
        "current_month": {"total_itc": 0},
        "percentage_change": 0,
        "disclaimer": "ITC estimates based on current scans",
        "supplier_breakdown": []
    }

@app.get("/")
async def root():
    return {"message": "Enterprise GST Scanner API", "auth": "UUID-RBAC Ready"}