import pytest
from app.worker.retry import calculate_full_jitter_delay


def test_calculate_full_jitter_delay_range():
    # Retry 1: 2^1 = 2
    delays_1 = [calculate_full_jitter_delay(1, cap=300) for _ in range(50)]
    for d in delays_1:
        assert 0.1 <= d <= 2.0

    # Retry 3: 2^3 = 8
    delays_3 = [calculate_full_jitter_delay(3, cap=300) for _ in range(50)]
    for d in delays_3:
        assert 0.1 <= d <= 8.0

    # Retries must exhibit variance (not deterministic identical numbers)
    assert len(set(delays_3)) > 10


def test_calculate_full_jitter_delay_cap():
    cap = 10.0
    # Retry 10: 2^10 = 1024, but cap is 10
    delays = [calculate_full_jitter_delay(10, cap=cap) for _ in range(50)]
    for d in delays:
        assert 0.1 <= d <= cap

