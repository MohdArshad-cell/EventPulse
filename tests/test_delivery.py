import pytest
import httpx
import respx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.client import Client, ClientState
from app.models.subscription import EventSubscription
from app.models.webhook_event import WebhookEvent, EventState
from app.models.dead_letter import DeadLetter
from app.models.delivery_attempt import DeliveryAttempt
from app.worker.tasks import async_deliver_webhook
from app.services.signature import verify_signature
from app.config import settings


@pytest.mark.asyncio
async def test_successful_delivery_flow(db_session):
    target_url = "https://receiver.example.com/webhook"
    secret = "client_secret_xyz"

    # Setup client
    client = Client(
        name="Reliable Receiver",
        endpoint_url=target_url,
        secret=secret,
        state=ClientState.ACTIVE.value
    )
    db_session.add(client)
    await db_session.flush()

    sub = EventSubscription(client_id=client.id, event_type="order.created")
    db_session.add(sub)

    # Setup event
    event = WebhookEvent(
        event_type="order.created",
        payload={"order_id": 999, "total": 1500},
        sequence_id=1,
        state=EventState.PENDING.value
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    # Mock HTTP 200
    with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.post(target_url).mock(
            return_value=httpx.Response(200, json={"status": "received"})
        )

        outcome = await async_deliver_webhook(event.id, session=db_session)
        assert outcome["status"] == "DELIVERED"
        assert route.called

        # Verify cryptographic HMAC signature header sent in request
        last_request = route.calls.last.request
        assert "X-Signature-Sha256" in last_request.headers or "x-signature-sha256" in last_request.headers
        sent_sig = last_request.headers.get("x-signature-sha256")
        assert verify_signature(event.payload, secret, sent_sig) is True

    # Verify DB records
    refetched_event = await db_session.get(WebhookEvent, event.id)
    assert refetched_event.state == EventState.DELIVERED.value


@pytest.mark.asyncio
async def test_failure_retry_and_dlq_flow(db_session):
    target_url = "https://failing-receiver.example.com/webhook"
    settings.MAX_RETRIES = 2

    # Setup client
    client = Client(
        name="Broken Receiver",
        endpoint_url=target_url,
        secret="broken_secret",
        state=ClientState.ACTIVE.value
    )
    db_session.add(client)
    await db_session.flush()

    sub = EventSubscription(client_id=client.id, event_type="payment.failed")
    db_session.add(sub)

    event = WebhookEvent(
        event_type="payment.failed",
        payload={"id": "err_1"},
        state=EventState.PENDING.value,
        retry_count=0
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.post(target_url).mock(
            return_value=httpx.Response(500, text="Crash")
        )

        # Attempt 1: Should schedule retry
        res1 = await async_deliver_webhook(event.id, session=db_session)
        assert res1["status"] == "SCHEDULED_RETRY"

        # Attempt 2 (hit max_retries=2): Should move to DLQ
        res2 = await async_deliver_webhook(event.id, session=db_session)
        assert res2["status"] == "FAILED_MOVED_TO_DLQ"

    # Verify DLQ record was created
    dlq_stmt = select(DeadLetter).where(DeadLetter.webhook_event_id == event.id)
    dlq_res = await db_session.execute(dlq_stmt)
    dlq = dlq_res.scalar_one_or_none()
    assert dlq is not None
    assert dlq.replayed is False
    assert "HTTP 500" in dlq.failure_reason
