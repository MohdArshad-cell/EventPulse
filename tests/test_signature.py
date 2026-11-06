import pytest
from app.services.signature import generate_secret, compute_signature, verify_signature


def test_generate_secret():
    secret1 = generate_secret()
    secret2 = generate_secret()
    assert len(secret1) == 64  # 32 bytes in hex = 64 characters
    assert secret1 != secret2


def test_compute_and_verify_signature_dict():
    secret = "my_super_secret"
    payload = {"event": "payment.success", "amount": 1000, "currency": "INR"}

    sig = compute_signature(payload, secret)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 is 64 hex characters

    # Verification must succeed
    assert verify_signature(payload, secret, sig) is True

    # Verification must fail if payload is tampered
    tampered_payload = {"event": "payment.success", "amount": 9999, "currency": "INR"}
    assert verify_signature(tampered_payload, secret, sig) is False

    # Verification must fail if secret is wrong
    assert verify_signature(payload, "wrong_secret", sig) is False


def test_signature_deterministic_key_ordering():
    secret = "test_key"
    payload_a = {"z": 1, "a": 2}
    payload_b = {"a": 2, "z": 1}

    # Dicts with identical data in different insertion orders must produce the exact same signature
    assert compute_signature(payload_a, secret) == compute_signature(payload_b, secret)

