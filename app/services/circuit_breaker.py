import datetime
from typing import Tuple
from app.models.client import Client, ClientState
from app.config import settings


class CircuitBreakerService:
    @staticmethod
    def is_client_available(client: Client) -> Tuple[bool, str]:
        """
        Check if the client can receive webhook dispatches.
        Returns: (can_send: bool, status_reason: str)
        States:
          - ACTIVE: normal delivery
          - HALF_OPEN: paused period expired, single probe allowed
          - PAUSED: circuit open, deliveries stopped
        """
        if client.state == ClientState.ACTIVE.value:
            return True, "ACTIVE"

        now = datetime.datetime.now(datetime.timezone.utc)
        if client.paused_until is None or now >= client.paused_until:
            # Half-open: test probe
            return True, "HALF_OPEN"

        return False, f"PAUSED until {client.paused_until.isoformat()}"

    @staticmethod
    def record_failure(client: Client) -> bool:
        """
        Record a failure for the client.
        If consecutive_failures reaches threshold, trip to PAUSED.
        Returns True if the circuit just tripped.
        """
        client.consecutive_failures += 1
        threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD

        if client.consecutive_failures >= threshold:
            client.state = ClientState.PAUSED.value
            now = datetime.datetime.now(datetime.timezone.utc)
            reset_duration = datetime.timedelta(seconds=settings.CIRCUIT_BREAKER_RESET_SECONDS)
            client.paused_until = now + reset_duration
            return True

        return False

    @staticmethod
    def record_success(client: Client) -> None:
        """
        Reset consecutive failure count and restore to ACTIVE state.
        """
        client.consecutive_failures = 0
        if client.state == ClientState.PAUSED.value:
            client.state = ClientState.ACTIVE.value
            client.paused_until = None

    @staticmethod
    def force_resume(client: Client) -> None:
        """Admin override to manually restore a client to ACTIVE."""
        client.state = ClientState.ACTIVE.value
        client.consecutive_failures = 0
        client.paused_until = None

