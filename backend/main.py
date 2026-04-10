import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Response, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from parser import extract_invoice_data
from database import get_db, init_db
from models import User, Company, Invoice, JoinRequest
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
    allow_origins=[
        "https://gstinvoicescanner.netlify.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
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
async def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
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
    
    response.set_cookie(key="access_token", value=token, httponly=True, secure=False, samesite="lax")
    
    return {
        "user": {
            "id": user.id, 
            "email": user.email, 
            "name": user.name, 
            "role": user.role,
            "company_id": user.company_id
        }
    }

@app.post("/api/register")
async def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # SECURITY: Role is ALWAYS hardcoded server-side to 'owner' on self-registration.
    # Never trust the client to supply their own role — this prevents privilege escalation.
    hashed = hash_password(req.password)
    new_user = User(
        name=req.name, 
        email=req.email, 
        password_hash=hashed, 
        role='owner'   # ← hardcoded: client cannot inject a role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    response.set_cookie(key="access_token", value=token, httponly=True, secure=False, samesite="lax")
    
    return {
        "user": {"id": new_user.id, "email": new_user.email, "role": new_user.role}
    }

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", secure=False, httponly=True, samesite="lax")
    return {"message": "Logged out successfully"}

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

@app.post("/api/join-request")
async def request_join_company(
    req: JoinCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Employee sends a join request — owner must approve before access is granted."""
    if current_user.company_id:
        raise HTTPException(status_code=400, detail="You are already part of a company")

    company = db.query(Company).filter(Company.name == req.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found. Check the exact name.")

    # Prevent duplicate requests
    existing = db.query(JoinRequest).filter(
        JoinRequest.user_id == current_user.id,
        JoinRequest.company_id == company.id,
        JoinRequest.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending request for this company")

    jr = JoinRequest(user_id=current_user.id, company_id=company.id)
    db.add(jr)
    db.commit()
    return {"message": "Join request sent. Waiting for owner approval.", "request_id": str(jr.id)}

@app.get("/api/join-requests")
async def list_join_requests(
    current_user: User = Depends(RoleChecker(['owner'])),
    db: Session = Depends(get_db)
):
    """Owner fetches all pending join requests for their company."""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="You don't have a company yet")

    requests = db.query(JoinRequest).filter(
        JoinRequest.company_id == current_user.company_id,
        JoinRequest.status == "pending"
    ).all()

    return [{
        "id": str(r.id),
        "user_id": str(r.user_id),
        "name": r.user.name,
        "email": r.user.email,
        "created_at": r.created_at.isoformat()
    } for r in requests]

@app.post("/api/join-requests/{request_id}/approve")
async def approve_join_request(
    request_id: str,
    current_user: User = Depends(RoleChecker(['owner'])),
    db: Session = Depends(get_db)
):
    """Owner approves a join request — links employee to the company."""
    jr = db.query(JoinRequest).filter(JoinRequest.id == request_id).first()
    if not jr or str(jr.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=404, detail="Request not found")

    employee = db.query(User).filter(User.id == jr.user_id).first()
    employee.company_id = current_user.company_id
    employee.role = "employee"
    jr.status = "accepted"
    db.commit()
    return {"message": f"{employee.name} has been added to your workspace"}

@app.post("/api/join-requests/{request_id}/reject")
async def reject_join_request(
    request_id: str,
    current_user: User = Depends(RoleChecker(['owner'])),
    db: Session = Depends(get_db)
):
    """Owner rejects a join request."""
    jr = db.query(JoinRequest).filter(JoinRequest.id == request_id).first()
    if not jr or str(jr.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=404, detail="Request not found")

    jr.status = "rejected"
    db.commit()
    return {"message": "Request rejected"}

@app.get("/api/join-request/status")
async def my_join_request_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Employee polls this to check if they've been approved."""
    if current_user.company_id:
        return {"status": "approved", "company_id": str(current_user.company_id)}

    jr = db.query(JoinRequest).filter(
        JoinRequest.user_id == current_user.id
    ).order_by(JoinRequest.created_at.desc()).first()

    if not jr:
        return {"status": "none"}
    return {"status": jr.status, "company_name": jr.company.name}

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
    
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    # SECURITY: Return only safe fields — never expose password_hash to the client.
    return [
        {"id": str(u.id), "name": u.name, "email": u.email, "role": u.role}
        for u in users
    ]

# ── Scan & Processing ─────────────────────────────────────────────────
# NOTE: We intentionally do NOT use an in-memory dict (scan_jobs = {}) for job
# state. Under Gunicorn with multiple workers, each process has isolated memory,
# so a job written in Worker-1 would be invisible to Workers 2-4 on a status
# poll. Instead, all job state is persisted to and read from the database.
# This makes the system worker-safe, horizontally scalable, and Cloud Run ready.

def process_invoice_background(job_id: str, file_bytes: bytes, content_type: str, user_id: uuid.UUID, company_id: uuid.UUID):
    from database import SessionLocal
    db = SessionLocal()
    try:
        data = extract_invoice_data(file_bytes, content_type)
        
        # Find the placeholder invoice record created at upload time
        invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
        if not invoice:
            return  # Record was deleted between upload and processing — abort silently
        
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
        
    except Exception as e:
        # Attempt to mark the job as FAILED in the DB even on unexpected errors
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

@app.post("/scan")
async def scan_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Please associate with a company first")
        
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")
        
    job_id = str(uuid.uuid4())
    
    # Create a placeholder DB record immediately so the status endpoint
    # always has a row to query — no in-memory dict required.
    placeholder = Invoice(
        job_id=job_id,
        company_id=current_user.company_id,
        uploaded_by=current_user.id,
        status="PROCESSING",
        raw_json={}
    )
    db.add(placeholder)
    db.commit()
    
    background_tasks.add_task(
        process_invoice_background, 
        job_id, contents, file.content_type, current_user.id, current_user.company_id
    )
    return {"job_id": job_id, "status": "processing"}

@app.get("/scan/status/{job_id}")
async def get_scan_status(job_id: str, db: Session = Depends(get_db)):
    """
    DB-backed status check — safe across multiple Gunicorn workers and Cloud Run instances.
    """
    invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if invoice.status == "PROCESSING":
        return {"status": "processing"}
    
    if invoice.status == "FAILED":
        return {"status": "failed", "error": invoice.error_message or "Extraction failed"}
    
    # SUCCESS — reconstruct the full result payload
    data = invoice.raw_json or {}
    data["id"] = str(invoice.id)
    data["status"] = "completed"
    data["health_score"] = calculate_health_score(data)
    return data

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
    from sqlalchemy import func, desc, extract
    if not current_user.company_id:
        return {}
    
    company_id = current_user.company_id
    base_query = db.query(Invoice).filter(Invoice.company_id == company_id, Invoice.status == "SUCCESS")
    
    totals = base_query.with_entities(
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total).label('spend'),
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst).label('tax')
    ).first()
    
    monthly_data = base_query.with_entities(
        extract('year', Invoice.created_at).label('year'),
        extract('month', Invoice.created_at).label('month'),
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total).label('total'),
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst).label('tax')
    ).group_by('year', 'month').order_by('year', 'month').all()

    monthly_spend = []
    monthly_invoice_count = []
    for row in monthly_data:
        m_str = f"{int(row.year)}-{int(row.month):02d}"
        monthly_spend.append({
            "month": m_str,
            "total": row.total or 0,
            "tax": row.tax or 0
        })
        monthly_invoice_count.append({
            "month": m_str,
            "count": row.count or 0
        })

    suppliers = base_query.with_entities(
        Invoice.seller_name,
        func.sum(Invoice.total).label('total_spend')
    ).filter(Invoice.seller_name.isnot(None))\
     .group_by(Invoice.seller_name)\
     .order_by(desc('total_spend'))\
     .limit(5).all()
     
    top_suppliers = [{"name": s.seller_name, "total_spend": s.total_spend or 0} for s in suppliers]
    
    return {
        "total_invoices": totals.count or 0 if totals else 0,
        "total_spend": totals.spend or 0 if totals else 0,
        "total_tax": totals.tax or 0 if totals else 0,
        "monthly_spend": monthly_spend,
        "top_suppliers": top_suppliers,
        "monthly_invoice_count": monthly_invoice_count
    }

@app.get("/api/itc-summary")
async def get_itc_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func, extract
    from datetime import datetime
    if not current_user.company_id:
        return {}

    now = datetime.utcnow()
    company_id = current_user.company_id
    
    curr_month = db.query(
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst)
    ).filter(
        Invoice.company_id == company_id, 
        Invoice.status == "SUCCESS",
        extract('year', Invoice.created_at) == now.year,
        extract('month', Invoice.created_at) == now.month
    ).scalar() or 0

    prev_month_date = now.month - 1 if now.month > 1 else 12
    prev_year_date = now.year if now.month > 1 else now.year - 1
    
    prev_month = db.query(
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst)
    ).filter(
        Invoice.company_id == company_id, 
        Invoice.status == "SUCCESS",
        extract('year', Invoice.created_at) == prev_year_date,
        extract('month', Invoice.created_at) == prev_month_date
    ).scalar() or 0

    pct_change = 0
    if prev_month > 0:
        pct_change = round(((curr_month - prev_month) / prev_month) * 100, 1)
    elif curr_month > 0:
        pct_change = 100

    suppliers = db.query(
        Invoice.seller_name,
        Invoice.seller_gstin,
        func.sum(Invoice.cgst).label('cgst'),
        func.sum(Invoice.sgst).label('sgst'),
        func.sum(Invoice.igst).label('igst'),
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst).label('total_itc')
    ).filter(
        Invoice.company_id == company_id,
        Invoice.status == "SUCCESS",
        extract('year', Invoice.created_at) == now.year,
        extract('month', Invoice.created_at) == now.month,
        Invoice.seller_name.isnot(None)
    ).group_by(Invoice.seller_name, Invoice.seller_gstin).all()
    
    supplier_breakdown = [{
        "seller_name": s.seller_name,
        "seller_gstin": s.seller_gstin or "UNKNOWN",
        "cgst": s.cgst or 0,
        "sgst": s.sgst or 0,
        "igst": s.igst or 0,
        "total_itc": s.total_itc or 0
    } for s in suppliers]

    return {
        "current_month": {"total_itc": curr_month},
        "percentage_change": pct_change,
        "disclaimer": "ITC estimates based on current scans and successfully processed invoices.",
        "supplier_breakdown": supplier_breakdown
    }

@app.get("/")
async def root():
    return {"message": "Enterprise GST Scanner API", "auth": "UUID-RBAC Ready"}