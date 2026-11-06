from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.webhook import WebhookIngestRequest, WebhookIngestResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post(
    "/webhooks/ingest",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a webhook event",
    description="Idempotent ingestion endpoint. Receives events, persists with state=PENDING, and triggers async dispatch."
)
async def ingest_webhook(
    request: WebhookIngestRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    event, is_created = await IngestionService.ingest_event(request, db)

    if not is_created:
        response.status_code = status.HTTP_200_OK
        return WebhookIngestResponse(
            event_id=event.id,
            status="ALREADY_PROCESSED",
            message=f"Event {event.id} already exists with state {event.state}."
        )

    return WebhookIngestResponse(
        event_id=event.id,
        status="ACCEPTED",
        message="Event accepted for delivery and queued."
    )

