"""FastAPI dependencies for the LifeLog API."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security_scheme = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
):
    """Dependency to validate the token from the request header.

    Args:
        credentials (HTTPAuthorizationCredentials): The credentials from the Authorization header.

    Returns:
        str: The validated token.

    Raises:
        HTTPException: If the token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if token != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
