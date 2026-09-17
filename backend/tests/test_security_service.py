import time
import uuid
import pytest
from django.conf import settings
from accounts.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    SecurityError,
)
from accounts.models import PlatformAdmin, StaffMember, Operator


def test_password_hashing_and_verification():
    raw_pwd = "SuperSecretPassword123@#"
    hashed = hash_password(raw_pwd)
    
    assert hashed != raw_pwd
    assert hashed.startswith("pbkdf2_sha256$") or len(hashed) > 40
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_access_token_lifecycle():
    user_id = str(uuid.uuid4())
    operator_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "email": "master@expressoneves.com.br",
        "role": "platform_admin",
        "is_platform_admin": True,
        "operator_id": operator_id,
    }
    
    token = create_access_token(payload, expires_in_minutes=15)
    assert isinstance(token, str)
    assert len(token) > 20
    
    decoded = decode_token(token)
    assert decoded["sub"] == user_id
    assert decoded["email"] == "master@expressoneves.com.br"
    assert decoded["role"] == "platform_admin"
    assert decoded["is_platform_admin"] is True
    assert decoded["operator_id"] == operator_id
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_refresh_token_lifecycle():
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "type": "refresh",
    }
    
    token = create_refresh_token(payload, expires_in_days=7)
    decoded = decode_token(token)
    assert decoded["sub"] == user_id
    assert decoded["type"] == "refresh"


def test_jwt_expired_token():
    payload = {"sub": "user-123"}
    # Token with negative expiry (already expired)
    token = create_access_token(payload, expires_in_minutes=-5)
    
    with pytest.raises(SecurityError, match="Token expirado"):
        decode_token(token)


def test_jwt_tampered_token():
    payload = {"sub": "user-123"}
    token = create_access_token(payload, expires_in_minutes=15)
    tampered_token = token[:-5] + "XXXXX"
    
    with pytest.raises(SecurityError, match="Token inválido"):
        decode_token(tampered_token)


def test_platform_admin_model_password_methods():
    admin = PlatformAdmin(
        id=uuid.uuid4(),
        name="Admin Test",
        email="admin@test.com",
    )
    admin.set_password("AdminPass123!")
    assert admin.passwordHash is not None
    assert admin.check_password("AdminPass123!") is True
    assert admin.check_password("WrongPass") is False


def test_staff_member_model_password_methods():
    staff = StaffMember(
        id=uuid.uuid4(),
        name="Staff Test",
        email="staff@test.com",
    )
    staff.set_password("StaffPass123!")
    assert staff.passwordHash is not None
    assert staff.check_password("StaffPass123!") is True
    assert staff.check_password("WrongPass") is False
