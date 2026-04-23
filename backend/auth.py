import os
from datetime import datetime
from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User
from typing import List
import uuid

load_dotenv()

# Supabase JWT Secret is used to verify tokens issued by Supabase Auth
SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is missing")
SECRET_KEY = SECRET_KEY.strip()

ALGORITHM = "HS256"

def decode_access_token(token: str) -> dict:
    try:
        # Supabase uses HS256 with the JWT Secret
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="authenticated")
        return payload
    except JWTError as e:
        print(f"JWT Verification Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Fallback for local development or older clients
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
        )

    payload = decode_access_token(token)
    
    # Supabase tokens use 'sub' for the user's UUID
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Sync Supabase user with our local database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Auto-create user record in our database if it doesn't exist
        # This ensures foreign key constraints for invoices/companies work
        user = User(
            id=uuid.UUID(user_id),
            email=email,
            name=payload.get("user_metadata", {}).get("full_name") or email.split('@')[0],
            role="owner", # Default role for new signups
            password_hash="SUPABASE_AUTH" # Placeholder as password is managed by Supabase
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            # If email already exists but with different ID, handle it
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(status_code=500, detail="Failed to sync user profile")

    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted to roles: {', '.join(self.allowed_roles)}",
            )
        return user

