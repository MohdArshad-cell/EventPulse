import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal, init_db
from app.models.client import Client, ClientState
from app.models.subscription import EventSubscription
from app.services.signature import generate_secret


async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        demo_clients = [
            {
                "name": "Stripe Payments Webhook Consumer",
                "endpoint_url": "https://httpbin.org/post",
                "secret": generate_secret(),
                "event_types": ["payment.*", "invoice.paid"]
            },
            {
                "name": "GitHub CI Sync Service",
                "endpoint_url": "https://httpbin.org/post",
                "secret": generate_secret(),
                "event_types": ["push", "pull_request.*"]
            },
            {
                "name": "Global Audit Logger",
                "endpoint_url": "https://httpbin.org/post",
                "secret": generate_secret(),
                "event_types": ["*"]
            }
        ]

        print("🌱 Seeding demo webhook subscribers...")
        for data in demo_clients:
            client = Client(
                name=data["name"],
                endpoint_url=data["endpoint_url"],
                secret=data["secret"],
                state=ClientState.ACTIVE.value,
                consecutive_failures=0
            )
            session.add(client)
            await session.flush()

            for pattern in data["event_types"]:
                sub = EventSubscription(client_id=client.id, event_type=pattern)
                session.add(sub)

            print(f"  ✓ Created client: {client.name} (ID: {client.id})")

        await session.commit()
        print("✅ Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())

