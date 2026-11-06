import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "healthy"
    assert "status" in data


@pytest.mark.asyncio
async def test_ingest_webhook_new_and_idempotency(client: AsyncClient):
    payload = {
        "event_id": "test_evt_1001",
        "event_type": "payment.success",
        "payload": {"amount": 500, "user_id": "u_99"},
        "sequence_id": 1
    }

    # 1. First ingestion -> 202 ACCEPTED
    res1 = await client.post("/api/v1/webhooks/ingest", json=payload)
    assert res1.status_code == 202
    data1 = res1.json()
    assert data1["event_id"] == "test_evt_1001"
    assert data1["status"] == "ACCEPTED"

    # 2. Duplicate ingestion -> 200 ALREADY_PROCESSED (Idempotency)
    res2 = await client.post("/api/v1/webhooks/ingest", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["event_id"] == "test_evt_1001"
    assert data2["status"] == "ALREADY_PROCESSED"


@pytest.mark.asyncio
async def test_client_crud_and_subscriptions(client: AsyncClient):
    headers = {"X-Admin-Key": "test_admin_key"}

    # 1. Register Client
    create_body = {
        "name": "Integration Partner",
        "endpoint_url": "https://example.com/webhook",
        "event_types": ["payment.*", "invoice.created"]
    }
    res = await client.post("/api/v1/clients", json=create_body, headers=headers)
    assert res.status_code == 201
    created = res.json()
    client_id = created["id"]
    assert created["name"] == "Integration Partner"
    assert len(created["subscriptions"]) == 2

    # 2. List Clients
    list_res = await client.get("/api/v1/clients", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Get Single Client
    get_res = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == client_id

    # 4. Update Subscriptions
    update_res = await client.put(
        f"/api/v1/clients/{client_id}/subscriptions",
        json={"event_types": ["order.*"]},
        headers=headers
    )
    assert update_res.status_code == 200
    assert len(update_res.json()["subscriptions"]) == 1
    assert update_res.json()["subscriptions"][0]["event_type"] == "order.*"

