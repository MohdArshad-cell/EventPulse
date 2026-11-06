"""
Interactive Webhook Receiver Mock Server
Use this to locally receive and verify webhooks dispatched by EventPulse.
"""
import sys
import os
import argparse
import asyncio
from fastapi import FastAPI, Request, Response, status
import uvicorn

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.signature import verify_signature

receiver_app = FastAPI(title="EventPulse Mock Webhook Consumer")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "eventpulse_super_secret_signing_key_change_me")
SIMULATE_STATUS = 200
SIMULATE_DELAY = 0.0


@receiver_app.post("/webhook")
async def receive_webhook(request: Request):
    headers = dict(request.headers)
    body = await request.json()

    event_id = headers.get("x-event-id", "unknown")
    event_type = headers.get("x-event-type", "unknown")
    sequence_id = headers.get("x-sequence-id", "unknown")
    signature = headers.get("x-signature-sha256", "")

    print("\n" + "=" * 60)
    print(f"📩 RECEIVED WEBHOOK EVENT: {event_type}")
    print(f"   Event ID    : {event_id}")
    print(f"   Sequence ID : {sequence_id}")
    print(f"   Signature   : {signature}")

    # Verify HMAC
    is_valid = verify_signature(body, CLIENT_SECRET, signature) if signature else False
    if is_valid:
        print("   Verification: ✅ VALID HMAC-SHA256 SIGNATURE")
    else:
        print("   Verification: ❌ INVALID OR MISSING SIGNATURE")

    print(f"   Payload     : {body}")
    print("=" * 60)

    if SIMULATE_DELAY > 0:
        print(f"⏳ Simulating slow response: sleeping {SIMULATE_DELAY}s...")
        await asyncio.sleep(SIMULATE_DELAY)

    if SIMULATE_STATUS != 200:
        print(f"⚠️ Simulating error response: HTTP {SIMULATE_STATUS}")
        return Response(content=f"Simulated Error {SIMULATE_STATUS}", status_code=SIMULATE_STATUS)

    return {"status": "ok", "message": "Webhook processed successfully"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mock Webhook Receiver")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on (default 9000)")
    parser.add_argument("--status", type=int, default=200, help="Simulated HTTP status code (e.g. 200, 500, 429)")
    parser.add_argument("--delay", type=float, default=0.0, help="Simulated delay in seconds")
    parser.add_argument("--secret", type=str, default="eventpulse_super_secret_signing_key_change_me")

    args = parser.parse_args()
    SIMULATE_STATUS = args.status
    SIMULATE_DELAY = args.delay
    CLIENT_SECRET = args.secret

    print(f"🚀 Starting EventPulse Mock Webhook Consumer on http://localhost:{args.port}/webhook")
    print(f"   Status Code: {SIMULATE_STATUS} | Delay: {SIMULATE_DELAY}s")
    uvicorn.run(receiver_app, host="0.0.0.0", port=args.port)
