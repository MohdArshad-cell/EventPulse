import pytest
from app.worker.tasks import matches_subscription


def test_matches_subscription_wildcard_all():
    assert matches_subscription("*", "payment.success") is True
    assert matches_subscription("*", "order.cancelled") is True
    assert matches_subscription("*", "custom.event.deep.nested") is True


def test_matches_subscription_prefix_wildcard():
    assert matches_subscription("payment.*", "payment.success") is True
    assert matches_subscription("payment.*", "payment.failed") is True
    assert matches_subscription("payment.*", "order.created") is False


def test_matches_subscription_exact():
    assert matches_subscription("order.created", "order.created") is True
    assert matches_subscription("order.created", "order.cancelled") is False
    assert matches_subscription("order.created", "order.created.nested") is False

