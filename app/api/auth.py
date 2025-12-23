"""API router for Authentication."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_current_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request schema for login."""

    password: str


class TokenResponse(BaseModel):
    """Response schema for token rotation."""

    api_token: str


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


@router.post("/token/rotate", response_model=TokenResponse)
async def rotate_token(request: LoginRequest, token: Annotated[str, Depends(get_current_token)]):
    """Rotate the API token. Requires admin password."""
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    new_token = secrets.token_urlsafe(32)
    # NOTE: In a production app, we would persist this new_token to the DB
    # or .env file. For this implementation, we return it but it won't
    # magically update settings.APP_AUTH_API_TOKEN in memory without a restart
    # or a persistent settings model.

    return {"api_token": new_token}
