from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.clients import router as clients_router
from app.api.v1.admin import router as admin_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(health_router)
v1_router.include_router(ingest_router)
v1_router.include_router(clients_router)
v1_router.include_router(admin_router)

