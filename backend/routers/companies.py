from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from auth import get_current_user, hash_password, RoleChecker
from database import get_db
from models import User, Company, JoinRequest
from schemas import (
    CompanyCreate, CompanyOut,
    JoinCompanyRequest, JoinRequestOut, JoinRequestStatusResponse,
    InviteUserRequest, InviteResponse,
    MessageResponse, UserListItem,
)

router = APIRouter(prefix="/api", tags=["companies"])


@router.post("/companies", response_model=CompanyOut)
async def create_company(
    req: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.company_id:
        raise HTTPException(status_code=400, detail="User already belongs to a company")

    existing = db.query(Company).filter(Company.gstin == req.gstin).first()
    if existing:
        raise HTTPException(status_code=400, detail="GSTIN already registered")

    company = Company(name=req.name, gstin=req.gstin, owner_id=current_user.id)
    db.add(company)
    db.flush()

    current_user.company_id = company.id
    current_user.role = "owner"
    db.commit()
    db.refresh(company)

    emp_count = db.query(User).filter(User.company_id == company.id).count()
    return CompanyOut(
        id=company.id,
        name=company.name,
        gstin=company.gstin,
        owner_id=company.owner_id,
        employee_count=emp_count,
    )


@router.get("/companies", response_model=List[CompanyOut])
async def get_my_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        return []

    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        return []

    emp_count = db.query(User).filter(User.company_id == company.id).count()
    return [CompanyOut(
        id=company.id,
        name=company.name,
        gstin=company.gstin,
        owner_id=company.owner_id,
        employee_count=emp_count,
    )]


@router.post("/join-request", response_model=MessageResponse)
async def request_join_company(
    req: JoinCompanyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Employee sends a join request — owner must approve before access is granted."""
    if current_user.company_id:
        raise HTTPException(status_code=400, detail="You are already part of a company")

    company = db.query(Company).filter(Company.name == req.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found. Check the exact name.")

    # Item 14: block if already accepted; allow re-apply if rejected; block duplicate pending
    existing = db.query(JoinRequest).filter(
        JoinRequest.user_id == current_user.id,
        JoinRequest.company_id == company.id,
    ).order_by(JoinRequest.created_at.desc()).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="You are already a member of this company")
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="You already have a pending request for this company")
        # status == "rejected" → allow re-application by creating a new request

    jr = JoinRequest(user_id=current_user.id, company_id=company.id)
    db.add(jr)
    db.commit()
    return MessageResponse(message="Join request sent. Waiting for owner approval.")


@router.get("/join-requests", response_model=List[JoinRequestOut])
async def list_join_requests(
    current_user: User = Depends(RoleChecker(["owner"])),
    db: Session = Depends(get_db),
):
    """Owner fetches all pending join requests for their company."""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="You don't have a company yet")

    requests = db.query(JoinRequest).filter(
        JoinRequest.company_id == current_user.company_id,
        JoinRequest.status == "pending",
    ).all()

    return [
        JoinRequestOut(
            id=str(r.id),
            user_id=str(r.user_id),
            name=r.user.name,
            email=r.user.email,
            created_at=r.created_at.isoformat(),
        )
        for r in requests
    ]


@router.post("/join-requests/{request_id}/approve", response_model=MessageResponse)
async def approve_join_request(
    request_id: str,
    current_user: User = Depends(RoleChecker(["owner"])),
    db: Session = Depends(get_db),
):
    jr = db.query(JoinRequest).filter(JoinRequest.id == request_id).first()
    if not jr or str(jr.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=404, detail="Request not found")

    employee = db.query(User).filter(User.id == jr.user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="User not found")

    # Guard against race condition: check employee doesn't already have a company
    if employee.company_id and str(employee.company_id) != str(current_user.company_id):
        jr.status = "rejected"
        db.commit()
        raise HTTPException(status_code=409, detail="User already belongs to another company")

    employee.company_id = current_user.company_id
    employee.role = "employee"
    jr.status = "accepted"
    db.commit()
    return MessageResponse(message=f"{employee.name} has been added to your workspace")


@router.post("/join-requests/{request_id}/reject", response_model=MessageResponse)
async def reject_join_request(
    request_id: str,
    current_user: User = Depends(RoleChecker(["owner"])),
    db: Session = Depends(get_db),
):
    jr = db.query(JoinRequest).filter(JoinRequest.id == request_id).first()
    if not jr or str(jr.company_id) != str(current_user.company_id):
        raise HTTPException(status_code=404, detail="Request not found")

    jr.status = "rejected"
    db.commit()
    return MessageResponse(message="Request rejected")


@router.get("/join-request/status", response_model=JoinRequestStatusResponse)
async def my_join_request_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.company_id:
        return JoinRequestStatusResponse(
            status="approved",
            company_id=str(current_user.company_id),
        )

    jr = db.query(JoinRequest).filter(
        JoinRequest.user_id == current_user.id,
    ).order_by(JoinRequest.created_at.desc()).first()

    if not jr:
        return JoinRequestStatusResponse(status="none")
    return JoinRequestStatusResponse(status=jr.status, company_name=jr.company.name)


@router.post("/invite-user", response_model=InviteResponse)
async def invite_user(
    req: InviteUserRequest,
    current_user: User = Depends(RoleChecker(["owner"])),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already registered")

    new_employee = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="employee",
        company_id=current_user.company_id,
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return InviteResponse(message="User invited and added to company", id=new_employee.id)


@router.get("/users", response_model=List[UserListItem])
async def list_company_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User not part of a company")

    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    # SECURITY: never expose password_hash
    return [
        UserListItem(id=str(u.id), name=u.name, email=u.email, role=u.role)
        for u in users
    ]
