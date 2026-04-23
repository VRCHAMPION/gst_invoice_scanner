from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from auth import (
    get_current_user,
)
from database import get_db
from models import User
from schemas import (
    UserOut, MessageResponse,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """
    Returns the current user profile. 
    The get_current_user dependency already handles syncing the Supabase user 
    to our local database.
    """
    return UserOut.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Clears the local access_token cookie if it exists.
    Supabase frontend SDK handles the primary logout.
    """
    response.delete_cookie(
        "access_token",
        secure=True,
        httponly=True,
        samesite="none",
    )
    return MessageResponse(message="Logged out successfully")

