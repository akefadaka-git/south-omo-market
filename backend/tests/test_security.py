from app.security import hash_password, verify_password


def test_password_hash_verifies_without_storing_plaintext() -> None:
    raw = "synthetic-test-password-123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("wrong-password-123", hashed)
