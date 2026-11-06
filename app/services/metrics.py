import time
from typing import Dict
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, ClientState
from app.models.webhook_event import WebhookEvent, EventState
from app.models.dead_letter import DeadLetter


class MetricsCollector:
    """
    Lightweight, thread-safe Prometheus metrics collector for EventPulse.
    Generates standard Prometheus exposition text format (version=0.0.4).
    """
    def __init__(self):
        # In-memory counters
        self.ingested_count: Dict[str, int] = defaultdict(int)
        self.delivery_success_count: Dict[str, int] = defaultdict(int)
        self.delivery_failure_count: Dict[str, int] = defaultdict(int)
        self.circuit_breaker_trips: Dict[str, int] = defaultdict(int)

    def record_ingest(self, event_type: str) -> None:
        self.ingested_count[event_type] += 1

    def record_delivery_success(self, client_id: str, event_type: str) -> None:
        key = f"{client_id}|{event_type}"
        self.delivery_success_count[key] += 1

    def record_delivery_failure(self, client_id: str, event_type: str) -> None:
        key = f"{client_id}|{event_type}"
        self.delivery_failure_count[key] += 1

    def record_cb_trip(self, client_id: str) -> None:
        self.circuit_breaker_trips[client_id] += 1

    async def generate_prometheus_metrics(self, db: AsyncSession) -> str:
        """Query DB and memory counters to render standard Prometheus metrics text."""
        lines = []

        # 1. Total Ingested
        lines.append("# HELP eventpulse_events_ingested_total Total webhook events received and queued")
        lines.append("# TYPE eventpulse_events_ingested_total counter")
        for event_type, count in self.ingested_count.items():
            lines.append(f'eventpulse_events_ingested_total{{event_type="{event_type}"}} {count}')

        # 2. Total Successful Deliveries
        lines.append("# HELP eventpulse_deliveries_success_total Total successful webhook deliveries (HTTP 2xx)")
        lines.append("# TYPE eventpulse_deliveries_success_total counter")
        for key, count in self.delivery_success_count.items():
            client_id, event_type = key.split("|", 1)
            lines.append(f'eventpulse_deliveries_success_total{{client_id="{client_id}",event_type="{event_type}"}} {count}')

        # 3. Total Failed Deliveries
        lines.append("# HELP eventpulse_deliveries_failed_total Total failed webhook deliveries (HTTP 5xx, timeouts)")
        lines.append("# TYPE eventpulse_deliveries_failed_total counter")
        for key, count in self.delivery_failure_count.items():
            client_id, event_type = key.split("|", 1)
            lines.append(f'eventpulse_deliveries_failed_total{{client_id="{client_id}",event_type="{event_type}"}} {count}')

        # 4. Circuit Breaker Trips
        lines.append("# HELP eventpulse_circuit_breaker_trips_total Total times client circuit was tripped to PAUSED")
        lines.append("# TYPE eventpulse_circuit_breaker_trips_total counter")
        for client_id, count in self.circuit_breaker_trips.items():
            lines.append(f'eventpulse_circuit_breaker_trips_total{{client_id="{client_id}"}} {count}')

        # 5. Database Gauges: Total Events in Queue / DLQ
        # Pending events
        pending_stmt = select(func.count(WebhookEvent.id)).where(WebhookEvent.state == EventState.PENDING.value)
        pending_res = await db.execute(pending_stmt)
        pending_count = pending_res.scalar() or 0

        lines.append("# HELP eventpulse_pending_events_gauge Current number of webhook events pending delivery")
        lines.append("# TYPE eventpulse_pending_events_gauge gauge")
        lines.append(f"eventpulse_pending_events_gauge {pending_count}")

        # DLQ events
        dlq_stmt = select(func.count(DeadLetter.id)).where(DeadLetter.replayed.is_(False))
        dlq_res = await db.execute(dlq_stmt)
        dlq_count = dlq_res.scalar() or 0

        lines.append("# HELP eventpulse_unreplayed_dlq_gauge Total unreplayed events in Dead Letter Queue")
        lines.append("# TYPE eventpulse_unreplayed_dlq_gauge gauge")
        lines.append(f"eventpulse_unreplayed_dlq_gauge {dlq_count}")

        # Active vs Paused Clients
        active_stmt = select(func.count(Client.id)).where(Client.state == ClientState.ACTIVE.value)
        active_res = await db.execute(active_stmt)
        active_count = active_res.scalar() or 0

        paused_stmt = select(func.count(Client.id)).where(Client.state == ClientState.PAUSED.value)
        paused_res = await db.execute(paused_stmt)
        paused_count = paused_res.scalar() or 0

        lines.append("# HELP eventpulse_clients_gauge Current number of registered clients by state")
        lines.append("# TYPE eventpulse_clients_gauge gauge")
        lines.append(f'eventpulse_clients_gauge{{state="ACTIVE"}} {active_count}')
        lines.append(f'eventpulse_clients_gauge{{state="PAUSED"}} {paused_count}')

        return "\n".join(lines) + "\n"


# Global singleton instance
metrics_collector = MetricsCollector()
