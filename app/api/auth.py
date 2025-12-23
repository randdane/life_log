"""API router for Authentication."""

import secrets

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request schema for login."""

    password: str


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """Web login for UI sessions (sets a placeholder cookie for now)."""
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # In a real app, we'd use a session manager or JWT
    response.set_cookie(
        key="session_id", value=secrets.token_urlsafe(32), httponly=True, samesite="lax"
    )
    return {"message": "Logged in successfully"}
