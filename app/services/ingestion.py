import logging
from typing import Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import WebhookEvent, EventState
from app.models.base import generate_uuid
from app.schemas.webhook import WebhookIngestRequest
from app.services.metrics import metrics_collector

logger = logging.getLogger(__name__)


class IngestionService:
    @staticmethod
    async def ingest_event(
        request: WebhookIngestRequest,
        db: AsyncSession
    ) -> Tuple[WebhookEvent, bool]:
        """
        Idempotent ingestion pipeline for webhook events.
        If the event_id is supplied and already exists, it returns (event, False).
        Otherwise creates a new record with state PENDING, dispatches the Celery delivery task,
        and returns (event, True).
        """
        event_id = request.event_id or generate_uuid()

        # Idempotency check
        stmt = select(WebhookEvent).where(WebhookEvent.id == event_id)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            logger.info(f"Duplicate event detected for idempotency key: {event_id}")
            return existing, False

        new_event = WebhookEvent(
            id=event_id,
            event_type=request.event_type,
            payload=request.payload,
            sequence_id=request.sequence_id or 1,
            state=EventState.PENDING.value,
            retry_count=0
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)

        # Record metrics
        metrics_collector.record_ingest(request.event_type)

        # Dispatch Celery worker task asynchronously
        try:
            from app.worker.tasks import deliver_webhook
            deliver_webhook.delay(event_id)
        except Exception as e:
            logger.warning(
                f"Celery broker not reachable immediately (task will be retried or swept): {e}"
            )

        return new_event, True
