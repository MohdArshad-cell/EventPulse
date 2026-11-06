import asyncio
import sys
import os
import httpx
import respx
from unittest.mock import MagicMock

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.worker.tasks import deliver_webhook
deliver_webhook.apply_async = MagicMock()
deliver_webhook.delay = MagicMock()

from app.db.session import AsyncSessionLocal, init_db
from app.models.client import Client, ClientState
from app.models.subscription import EventSubscription
from app.models.webhook_event import WebhookEvent, EventState
from app.worker.tasks import async_deliver_webhook
from app.services.signature import generate_secret


async def simulate():
    """
    Simulation script that runs locally without needing external network:
    1. Sets up a mock flaky recipient server.
    2. Sends webhooks and watches retry logic and DLQ movement.
    """
    await init_db()
    print("🔥 Starting Webhook Failure & Retry Simulation...")

    test_url = "https://unreliable-partner.api/webhook"

    async with AsyncSessionLocal() as session:
        # Create flaky client
        client = Client(
            name="Flaky Partner Receiver",
            endpoint_url=test_url,
            secret=generate_secret(),
            state=ClientState.ACTIVE.value,
            consecutive_failures=0
        )
        session.add(client)
        await session.flush()

        sub = EventSubscription(client_id=client.id, event_type="payment.failed")
        session.add(sub)

        # Create event
        event = WebhookEvent(
            event_type="payment.failed",
            payload={"customer_id": "cust_123", "amount": 9900, "currency": "INR"},
            sequence_id=42,
            state=EventState.PENDING.value
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        event_id = event.id
        print(f"Created Event {event_id} for client: {client.name}")

    # Use respx to simulate 500 Internal Server Errors
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.post(test_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error: DB down")
        )

        for attempt in range(1, 6):
            print(f"\n--- Running Attempt #{attempt} ---")
            result = await async_deliver_webhook(event_id)
            print(f"Outcome: {result}")

    print("\n✅ Simulation complete! Final state reached.")


if __name__ == "__main__":
    asyncio.run(simulate())
