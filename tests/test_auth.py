import hashlib
import pytest
from api.auth import hash_password, verify_password, ROLE_LEVEL


def test_hash_roundtrip():
    plain = "test_password_123"
    hashed = hash_password(plain)

    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)


def test_hash_different_each_time():
    plain = "test_password"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)

    assert hash1 != hash2
    assert verify_password(plain, hash1)
    assert verify_password(plain, hash2)


def test_role_level_hierarchy():
    assert ROLE_LEVEL["viewer"] == 1
    assert ROLE_LEVEL["editor"] == 2
    assert ROLE_LEVEL["admin"] == 3

    assert ROLE_LEVEL["viewer"] < ROLE_LEVEL["editor"] < ROLE_LEVEL["admin"]
