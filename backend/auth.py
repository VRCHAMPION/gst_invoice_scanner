import os
import json
import urllib.request
import uuid
from typing import List, Optional

from cachetools import TTLCache, cached
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is missing")
SECRET_KEY = SECRET_KEY.strip()

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is missing")
SUPABASE_URL = SUPABASE_URL.strip().rstrip("/")

ALGORITHM = "HS256"
COOKIE_NAME = "sb_session"
COOKIE_MAX_AGE = 3600  # matches Supabase default JWT expiry

IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"


# ── JWKS & Token Decoding ─────────────────────────────────────────────────────

@cached(cache=TTLCache(maxsize=1, ttl=600))
def get_jwks() -> dict:
    """Fetch and cache the JSON Web Key Set from Supabase for 10 minutes."""
    jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    req = urllib.request.Request(jwks_url)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def decode_access_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        
        if alg == "HS256":
            # Legacy symmetric token
            return jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            # Asymmetric token (ES256, RS256, etc.)
            jwks = get_jwks()
            kid = header.get("kid")
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            
            if not key:
                raise JWTError(f"Signing key {kid} not found in JWKS")
                
            return jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256", "EdDSA"],
                audience="authenticated",
            )
            
    except JWTError as e:
        import structlog
        structlog.get_logger().error("jwt_decode_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Cookie Helpers ────────────────────────────────────────────────────────────

def set_auth_cookie(response: Response, token: str) -> None:
    """Set a secure HttpOnly session cookie containing the Supabase JWT."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=IS_PRODUCTION,
        # SameSite=None required for cross-origin (Netlify frontend → Render backend)
        # When moved to same-domain, harden to "strict"
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Delete the session cookie on logout."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )


def _extract_token(request: Request) -> Optional[str]:
    """
    Extract JWT from:
      1. HttpOnly cookie  — primary (browser clients)
      2. Authorization: Bearer header — fallback (API clients, mobile apps)
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


# ── JIT User Sync ─────────────────────────────────────────────────────────────

def _sync_user(user_id: str, email: str, payload: dict, db: Session) -> User:
    """
    Look up the user in the local DB. If not found, create them (JIT sync).
    The local user UUID always matches the Supabase Auth UUID (sub claim).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=uuid.UUID(user_id),
            email=email,
            name=(
                payload.get("user_metadata", {}).get("full_name")
                or email.split("@")[0]
            ),
            role="owner",
            password_hash="SUPABASE_AUTH",
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                raise HTTPException(status_code=500, detail="Failed to sync user profile")
    return user


# ── Auth Dependency ───────────────────────────────────────────────────────────

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return _sync_user(user_id, email, payload, db)


# ── Role-Based Access Control ─────────────────────────────────────────────────

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
