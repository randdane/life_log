"""FastAPI dependencies for the LifeLog API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_token(token: str = Depends(oauth2_scheme)):
    """Dependency to validate the API token from the request header.

    Args:
        token (str): The token from the Authorization header.

    Returns:
        str: The validated token.

    Raises:
        HTTPException: If the token is invalid.
    """
    if settings.API_TOKEN and token != settings.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
