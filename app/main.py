from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import init_db, get_db
from app.api.router import api_router
from app.services.metrics import metrics_collector


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Production-grade, resilient webhook dispatcher system with exponential backoff, "
        "full jitter, HMAC-SHA256 verification, dead letter queues, and auto circuit-breaking."
    ),
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
        "metrics": "/metrics"
    }


@app.get("/metrics", tags=["Observability"], summary="Prometheus Metrics Scrape Endpoint")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Exposes real-time Prometheus format metrics for Grafana / Prometheus scraping."""
    content = await metrics_collector.generate_prometheus_metrics(db)
    return Response(content=content, media_type="text/plain; version=0.0.4")
