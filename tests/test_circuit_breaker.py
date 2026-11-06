import datetime
import pytest
from app.models.client import Client, ClientState
from app.services.circuit_breaker import CircuitBreakerService
from app.config import settings


def test_circuit_breaker_transitions():
    client = Client(
        name="Test Gateway",
        endpoint_url="https://api.test/webhook",
        secret="sec",
        state=ClientState.ACTIVE.value,
        consecutive_failures=0
    )

    can_send, reason = CircuitBreakerService.is_client_available(client)
    assert can_send is True
    assert reason == "ACTIVE"

    # Simulate failures below threshold
    settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
    tripped = CircuitBreakerService.record_failure(client)
    assert tripped is False
    assert client.consecutive_failures == 1

    tripped = CircuitBreakerService.record_failure(client)
    assert tripped is False
    assert client.consecutive_failures == 2

    # Third failure hits threshold -> Tripped!
    tripped = CircuitBreakerService.record_failure(client)
    assert tripped is True
    assert client.state == ClientState.PAUSED.value
    assert client.paused_until is not None

    can_send, reason = CircuitBreakerService.is_client_available(client)
    assert can_send is False
    assert "PAUSED" in reason

    # Simulate timeout passed (half-open)
    client.paused_until = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)
    can_send, reason = CircuitBreakerService.is_client_available(client)
    assert can_send is True
    assert reason == "HALF_OPEN"

    # Record success -> Restored to ACTIVE
    CircuitBreakerService.record_success(client)
    assert client.state == ClientState.ACTIVE.value
    assert client.consecutive_failures == 0
    assert client.paused_until is None


def test_circuit_breaker_force_resume():
    client = Client(
        name="Test",
        endpoint_url="https://api.test/webhook",
        secret="sec",
        state=ClientState.PAUSED.value,
        consecutive_failures=10,
        paused_until=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    )

    CircuitBreakerService.force_resume(client)
    assert client.state == ClientState.ACTIVE.value
    assert client.consecutive_failures == 0
    assert client.paused_until is None

