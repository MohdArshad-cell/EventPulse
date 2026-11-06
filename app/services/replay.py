import datetime
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter import DeadLetter
from app.models.webhook_event import WebhookEvent, EventState

logger = logging.getLogger(__name__)


class ReplayService:
    @staticmethod
    async def replay_single(
        dlq_id: str,
        db: AsyncSession
    ) -> Optional[DeadLetter]:
        """
        Replay a single DLQ event by resetting its WebhookEvent state and dispatching a worker task.
        """
        stmt = select(DeadLetter).where(DeadLetter.id == dlq_id)
        res = await db.execute(stmt)
        dlq_entry = res.scalar_one_or_none()

        if not dlq_entry:
            return None

        # Fetch associated WebhookEvent
        event_stmt = select(WebhookEvent).where(WebhookEvent.id == dlq_entry.webhook_event_id)
        event_res = await db.execute(event_stmt)
        event = event_res.scalar_one_or_none()

        if event:
            event.state = EventState.PENDING.value
            event.retry_count = 0
            event.next_retry_at = None

        dlq_entry.replayed = True
        dlq_entry.replayed_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(dlq_entry)

        # Enqueue delivery
        try:
            from app.worker.tasks import deliver_webhook
            deliver_webhook.delay(dlq_entry.webhook_event_id)
        except Exception as e:
            logger.warning(f"Could not dispatch Celery replay task: {e}")

        return dlq_entry

    @staticmethod
    async def bulk_replay(
        client_id: Optional[str],
        event_type: Optional[str],
        failed_after: Optional[datetime.datetime],
        spread_window_seconds: float,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Bulk replay matching Dead Letter Queue events with STAGGERED countdown delays.
        This prevents the 'Thundering Herd' issue when hundreds or thousands of failed
        events are replayed at once.
        """
        query = select(DeadLetter).where(DeadLetter.replayed.is_(False))

        if client_id:
            query = query.where(DeadLetter.client_id == client_id)
        if event_type:
            query = query.where(DeadLetter.event_type == event_type)
        if failed_after:
            query = query.where(DeadLetter.failed_at >= failed_after)

        res = await db.execute(query)
        matching_dlqs = res.scalars().all()

        total = len(matching_dlqs)
        if total == 0:
            return {
                "total_matching": 0,
                "replayed_count": 0,
                "spread_window_seconds": spread_window_seconds,
                "stagger_interval_seconds": 0.0,
                "message": "No unreplayed DLQ items matched the filter criteria."
            }

        stagger_interval = spread_window_seconds / total if total > 1 else 0.0
        now = datetime.datetime.now(datetime.timezone.utc)

        for i, dlq_entry in enumerate(matching_dlqs):
            stagger_delay = round(i * stagger_interval, 2)

            event_stmt = select(WebhookEvent).where(WebhookEvent.id == dlq_entry.webhook_event_id)
            event_res = await db.execute(event_stmt)
            event = event_res.scalar_one_or_none()
            if event:
                event.state = EventState.PENDING.value
                event.retry_count = 0
                event.next_retry_at = now + datetime.timedelta(seconds=stagger_delay)

            dlq_entry.replayed = True
            dlq_entry.replayed_at = now

            try:
                from app.worker.tasks import deliver_webhook
                deliver_webhook.apply_async(
                    args=[dlq_entry.webhook_event_id],
                    countdown=stagger_delay
                )
            except Exception as e:
                logger.warning(f"Failed to stagger Celery task for event {dlq_entry.webhook_event_id}: {e}")

        await db.commit()

        return {
            "total_matching": total,
            "replayed_count": total,
            "spread_window_seconds": spread_window_seconds,
            "stagger_interval_seconds": stagger_interval,
            "message": f"Successfully scheduled {total} DLQ events staggered across {spread_window_seconds}s."
        }
