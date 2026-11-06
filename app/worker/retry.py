import random
from app.config import settings


def calculate_full_jitter_delay(
    retry_count: int,
    base: float = 2.0,
    cap: float = None
) -> float:
    """
    Calculate exponential backoff delay with Full Jitter.
    
    Formula:
        Delay = random.uniform(0, min(cap, base ^ retry_count))
        
    Why Full Jitter?
    When thousands of webhooks fail simultaneously (e.g. client downtime),
    standard exponential backoff causes all retries to hit at the exact same second,
    creating a 'Thundering Herd' that instantly crashes the recovering server.
    Full Jitter uniformly redistributes retries across the entire interval [0, 2^retry_count],
    smoothing server traffic and maximizing recovery probability.
    """
    if cap is None:
        cap = settings.RETRY_CAP_SECONDS

    # 2 ^ retry_count
    max_interval = min(cap, base ** max(1, retry_count))
    # Full jitter selects uniform random between 0 and max_interval
    delay = random.uniform(0.1, max_interval)
    return round(delay, 3)

