import asyncio
import datetime
import time
import logging
from typing import Optional, List
import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.celery_app import celery
from app.worker.retry import calculate_full_jitter_delay
from app.db.session import AsyncSessionLocal
from app.models.webhook_event import WebhookEvent, EventState
from app.models.client import Client, ClientState
from app.models.delivery_attempt import DeliveryAttempt
from app.models.dead_letter import DeadLetter
from app.services.signature import compute_signature
from app.services.circuit_breaker import CircuitBreakerService
from app.config import settings

logger = logging.getLogger(__name__)


def matches_subscription(subscribed_pattern: str, event_type: str) -> bool:
    """Check if an event_type matches a client's subscription pattern."""
    if subscribed_pattern == "*" or subscribed_pattern == event_type:
        return True
    if subscribed_pattern.endswith(".*"):
        prefix = subscribed_pattern[:-2]
        return event_type == prefix or event_type.startswith(prefix + ".")
    return False


async def async_deliver_webhook(event_id: str, session: Optional[AsyncSession] = None) -> dict:
    """
    Async core execution logic for delivering a webhook event to all subscribed clients.
    Handles HMAC signing, HTTP dispatch, retries with Full Jitter, DLQ insertion,
    and Circuit Breaker state management.
    """
    if session is not None:
        return await _deliver_internal(event_id, session)
    else:
        async with AsyncSessionLocal() as new_session:
            return await _deliver_internal(event_id, new_session)


async def _deliver_internal(event_id: str, session: AsyncSession) -> dict:
    # Load event
    stmt = (
        select(WebhookEvent)
        .where(WebhookEvent.id == event_id)
        .options(selectinload(WebhookEvent.delivery_attempts))
    )
    res = await session.execute(stmt)
    event = res.scalar_one_or_none()

    if not event:
        logger.warning(f"Webhook event {event_id} not found")
        return {"status": "NOT_FOUND", "event_id": event_id}

    if event.state == EventState.DELIVERED.value:
        logger.info(f"Webhook event {event_id} already marked DELIVERED")
        return {"status": "ALREADY_DELIVERED", "event_id": event_id}

    event.state = EventState.DELIVERING.value
    await session.commit()

    # Find eligible clients with subscriptions
    client_stmt = select(Client).options(selectinload(Client.subscriptions))
    client_res = await session.execute(client_stmt)
    all_clients = client_res.scalars().all()

    matching_clients: List[Client] = []
    for client in all_clients:
        for sub in client.subscriptions:
            if matches_subscription(sub.event_type, event.event_type):
                matching_clients.append(client)
                break

    if not matching_clients:
        logger.info(f"No clients subscribed to event {event.event_type}")
        event.state = EventState.DELIVERED.value
        await session.commit()
        return {"status": "NO_SUBSCRIBERS", "event_id": event_id}

    has_any_failure = False
    last_failure_reason = ""

    # Deliver to each subscribed client
    for client in matching_clients:
        can_send, cb_status = CircuitBreakerService.is_client_available(client)
        if not can_send:
            logger.warning(
                f"Client {client.name} ({client.id}) is {cb_status}. Bypassing direct delivery to DLQ."
            )
            dlq_entry = DeadLetter(
                webhook_event_id=event.id,
                client_id=client.id,
                event_type=event.event_type,
                payload=event.payload,
                failure_reason=f"CIRCUIT_BREAKER_OPEN: {cb_status}"
            )
            session.add(dlq_entry)
            has_any_failure = True
            last_failure_reason = f"CIRCUIT_BREAKER_OPEN: {cb_status}"
            continue

        # Compute HMAC-SHA256 signature
        signature = compute_signature(event.payload, client.secret)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EventPulse-Webhook-Dispatcher/1.0",
            "X-Event-Id": str(event.id),
            "X-Event-Type": str(event.event_type),
            "X-Signature-SHA256": signature,
            "X-Sequence-Id": str(event.sequence_id),
        }

        attempt_number = len(event.delivery_attempts) + 1
        http_status = None
        error_message = None
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=settings.DELIVERY_TIMEOUT_SECONDS) as http_client:
                response = await http_client.post(
                    client.endpoint_url,
                    json=event.payload,
                    headers=headers
                )
                http_status = response.status_code
                response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if 200 <= response.status_code < 300:
                    CircuitBreakerService.record_success(client)
                else:
                    error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    CircuitBreakerService.record_failure(client)
                    has_any_failure = True
                    last_failure_reason = error_message

        except httpx.TimeoutException as exc:
            response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_message = f"Request timed out after {settings.DELIVERY_TIMEOUT_SECONDS}s: {str(exc)}"
            CircuitBreakerService.record_failure(client)
            has_any_failure = True
            last_failure_reason = error_message
        except Exception as exc:
            response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_message = f"Network or connection error: {str(exc)}"
            CircuitBreakerService.record_failure(client)
            has_any_failure = True
            last_failure_reason = error_message

        # Log delivery attempt
        attempt = DeliveryAttempt(
            webhook_event_id=event.id,
            client_id=client.id,
            attempt_number=attempt_number,
            http_status=http_status,
            error_message=error_message,
            response_time_ms=response_time_ms
        )
        session.add(attempt)

    # Handle final state and retry evaluation
    if not has_any_failure:
        event.state = EventState.DELIVERED.value
        event.next_retry_at = None
        await session.commit()
        return {"status": "DELIVERED", "event_id": event_id}
    else:
        event.retry_count += 1
        if event.retry_count >= settings.MAX_RETRIES:
            event.state = EventState.FAILED.value
            event.next_retry_at = None

            # Add to Dead Letter Queue for auditing & replay
            for client in matching_clients:
                dlq_entry = DeadLetter(
                    webhook_event_id=event.id,
                    client_id=client.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    failure_reason=last_failure_reason or "MAX_RETRIES_EXCEEDED"
                )
                session.add(dlq_entry)

            await session.commit()
            logger.error(f"Event {event_id} failed after {settings.MAX_RETRIES} attempts. Moved to DLQ.")
            return {"status": "FAILED_MOVED_TO_DLQ", "event_id": event_id}
        else:
            # Schedule retry with Full Jitter
            delay = calculate_full_jitter_delay(event.retry_count, cap=settings.RETRY_CAP_SECONDS)
            now = datetime.datetime.now(datetime.timezone.utc)
            event.next_retry_at = now + datetime.timedelta(seconds=delay)
            event.state = EventState.PENDING.value
            await session.commit()

            try:
                deliver_webhook.apply_async(args=[event_id], countdown=delay)
            except Exception as celery_err:
                logger.warning(f"Could not enqueue Celery retry automatically: {celery_err}")

            return {"status": "SCHEDULED_RETRY", "event_id": event_id, "delay_seconds": delay}


@celery.task(bind=True, name="app.worker.tasks.deliver_webhook")
def deliver_webhook(self, event_id: str) -> dict:
    """Celery task entrypoint."""
    return asyncio.run(async_deliver_webhook(event_id))


@celery.task(name="app.worker.tasks.circuit_breaker_sweep")
def circuit_breaker_sweep() -> dict:
    """Periodic Celery Beat task to check paused clients and restore expired timeouts."""
    async def _sweep():
        async with AsyncSessionLocal() as session:
            now = datetime.datetime.now(datetime.timezone.utc)
            stmt = select(Client).where(
                Client.state == ClientState.PAUSED.value,
                Client.paused_until <= now
            )
            res = await session.execute(stmt)
            paused_clients = res.scalars().all()
            unpaused = 0
            for client in paused_clients:
                CircuitBreakerService.record_success(client)
                unpaused += 1
            await session.commit()
            return {"unpaused_count": unpaused}

    return asyncio.run(_sweep())
