import hmac
import hashlib
import json
import secrets
from typing import Union, Dict, Any


def generate_secret(length: int = 32) -> str:
    """Generate a cryptographically secure random hexadecimal secret key."""
    return secrets.token_hex(length)


def _serialize_payload(payload: Union[bytes, str, Dict[str, Any], list]) -> bytes:
    """Consistently serialize any payload into bytes for signing."""
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    # Sort keys for deterministic JSON serialization
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def compute_signature(payload: Union[bytes, str, Dict[str, Any], list], secret: str) -> str:
    """
    Compute HMAC-SHA256 signature for the given payload and secret.
    Returns hex digest string.
    """
    secret_bytes = secret.encode("utf-8")
    payload_bytes = _serialize_payload(payload)
    return hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()


def verify_signature(
    payload: Union[bytes, str, Dict[str, Any], list],
    secret: str,
    provided_signature: str
) -> bool:
    """
    Verify HMAC-SHA256 signature using constant-time comparison to prevent timing attacks.
    """
    expected_signature = compute_signature(payload, secret)
    return hmac.compare_digest(expected_signature, provided_signature.strip())

