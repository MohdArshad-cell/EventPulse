from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint to verify database and redis connectivity."""
    db_status = "unhealthy"
    redis_status = "unhealthy"

    # Test Database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Test Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy (broker offline or unreachable): {str(e)}"

    overall_healthy = (db_status == "healthy")

    return {
        "status": "ok" if overall_healthy else "degraded",
        "database": db_status,
        "redis": redis_status,
        "environment": settings.ENVIRONMENT,
        "project": settings.PROJECT_NAME
    }

