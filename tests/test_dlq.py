import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.client import Client, ClientState
from app.models.webhook_event import WebhookEvent, EventState
from app.models.dead_letter import DeadLetter


@pytest.mark.asyncio
async def test_dlq_list_and_single_replay(client: AsyncClient, test_engine):
    headers = {"X-Admin-Key": "test_admin_key"}

    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        c = Client(name="Target", endpoint_url="https://test/cb", secret="s1", state=ClientState.ACTIVE.value)
        db.add(c)
        await db.flush()

        evt = WebhookEvent(
            event_type="order.failed",
            payload={"item": "book"},
            state=EventState.FAILED.value,
            retry_count=5
        )
        db.add(evt)
        await db.flush()

        dlq = DeadLetter(
            webhook_event_id=evt.id,
            client_id=c.id,
            event_type="order.failed",
            payload={"item": "book"},
            failure_reason="HTTP 503 Service Unavailable",
            replayed=False
        )
        db.add(dlq)
        await db.flush()

        dlq_id = dlq.id
        event_id = evt.id
        await db.commit()

    # 1. List DLQ
    list_res = await client.get("/api/v1/admin/dlq", headers=headers)
    assert list_res.status_code == 200
    entries = list_res.json()
    assert len(entries) >= 1
    assert any(e["id"] == dlq_id for e in entries)

    # 2. Replay single DLQ
    replay_res = await client.post(f"/api/v1/admin/dlq/{dlq_id}/replay", headers=headers)
    assert replay_res.status_code == 200
    replayed_entry = replay_res.json()
    assert replayed_entry["replayed"] is True

    # 3. Verify event state was reset to PENDING
    event_detail_res = await client.get(f"/api/v1/admin/events/{event_id}", headers=headers)
    assert event_detail_res.status_code == 200
    assert event_detail_res.json()["state"] == "PENDING"
    assert event_detail_res.json()["retry_count"] == 0


@pytest.mark.asyncio
async def test_dlq_bulk_replay_staggered(client: AsyncClient, test_engine):
    headers = {"X-Admin-Key": "test_admin_key"}
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        c = Client(name="Target2", endpoint_url="https://test/cb2", secret="s2", state=ClientState.ACTIVE.value)
        db.add(c)
        await db.flush()

        for i in range(3):
            evt = WebhookEvent(
                event_type="payment.refunded",
                payload={"refund_id": i},
                state=EventState.FAILED.value,
                retry_count=5
            )
            db.add(evt)
            await db.flush()

            dlq = DeadLetter(
                webhook_event_id=evt.id,
                client_id=c.id,
                event_type="payment.refunded",
                payload={"refund_id": i},
                failure_reason="Timeout",
                replayed=False
            )
            db.add(dlq)
        await db.commit()

    # Trigger bulk replay across a 30-second window
    body = {
        "filter": {"event_type": "payment.refunded"},
        "spread_window_seconds": 30.0
    }
    res = await client.post("/api/v1/admin/dlq/bulk-replay", json=body, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_matching"] == 3
    assert data["replayed_count"] == 3
    assert data["stagger_interval_seconds"] == 10.0  # 30s / 3 items = 10s interval
