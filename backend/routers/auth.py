from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import (
    get_current_user,
    set_auth_cookie,
    clear_auth_cookie,
    decode_access_token,
    _sync_user,
)
from database import get_db
from models import User
from schemas import UserOut, MessageResponse

router = APIRouter(prefix="/api", tags=["auth"])


class SessionRequest(BaseModel):
    access_token: str


@router.post("/auth/session", response_model=UserOut)
async def establish_session(
    req: SessionRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Token exchange endpoint. Validates a Supabase JWT sent in the request
    body, sets a secure HttpOnly cookie, and returns the user profile.

    Called by the frontend immediately after any Supabase sign-in
    (password, OAuth, magic link). After this call, all subsequent API
    requests use the cookie automatically — the raw token never needs
    to be stored in JS-accessible storage.
    """
    payload = decode_access_token(req.access_token)
    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = _sync_user(user_id, email, payload, db)
    set_auth_cookie(response, req.access_token)
    return UserOut.model_validate(user)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Returns the current authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Clears the HttpOnly session cookie.
    Frontend must also call supabase.auth.signOut() to clear the Supabase session.
    """
    clear_auth_cookie(response)
    return MessageResponse(message="Logged out successfully")
