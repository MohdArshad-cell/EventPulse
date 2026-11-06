from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.config import settings


async def verify_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
) -> str:
    """Dependency verifying administrative API key for management endpoints."""
    if not x_admin_key or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Key header"
        )
    return x_admin_key

