import time
from typing import Dict, Tuple
import threading


class TokenBucketRateLimiter:
    """
    Thread-safe in-memory Token Bucket rate limiter per client.
    Ensures outbound webhook dispatching respects client-specific throughput limits
    (e.g., max 20 requests per second) to prevent HTTP 429 Too Many Requests.
    """
    def __init__(self, default_rate: float = 50.0, default_capacity: float = 50.0):
        # rate: tokens added per second
        # capacity: burst bucket capacity
        self.default_rate = default_rate
        self.default_capacity = default_capacity
        self._buckets: Dict[str, Tuple[float, float]] = {}  # client_id -> (tokens, last_updated)
        self._lock = threading.Lock()

    def acquire(self, client_id: str, tokens: float = 1.0, rate: float = None, capacity: float = None) -> bool:
        """
        Attempt to acquire tokens for a given client_id.
        Returns True if tokens were acquired, False if rate limit is exceeded.
        """
        now = time.monotonic()
        r = rate or self.default_rate
        cap = capacity or self.default_capacity

        with self._lock:
            if client_id not in self._buckets:
                self._buckets[client_id] = (cap - tokens, now)
                return True

            current_tokens, last_time = self._buckets[client_id]
            # Refill tokens based on elapsed time
            elapsed = now - last_time
            current_tokens = min(cap, current_tokens + (elapsed * r))

            if current_tokens >= tokens:
                self._buckets[client_id] = (current_tokens - tokens, now)
                return True
            else:
                self._buckets[client_id] = (current_tokens, now)
                return False

    def reset(self, client_id: str) -> None:
        """Reset the bucket for a given client."""
        with self._lock:
            self._buckets.pop(client_id, None)


# Global rate limiter instance
client_rate_limiter = TokenBucketRateLimiter(default_rate=50.0, default_capacity=50.0)
