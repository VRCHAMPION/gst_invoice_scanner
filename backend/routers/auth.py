from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from auth import (
    get_current_user, hash_password, verify_password,
    create_access_token, COOKIE_SECURE, COOKIE_SAMESITE,
)
from database import get_db
from models import User
from schemas import (
    LoginRequest, RegisterRequest,
    AuthResponse, UserOut, MessageResponse,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None,
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )

    return AuthResponse(user=UserOut.model_validate(user))


@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")
async def register(
    request: Request,
    req: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # SECURITY: role is ALWAYS hardcoded server-side — never trust the client.
    new_user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role="owner",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={
        "sub": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
    })
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )

    return AuthResponse(user=UserOut.model_validate(new_user))


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    response.delete_cookie(
        "access_token",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite=COOKIE_SAMESITE,
    )
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
