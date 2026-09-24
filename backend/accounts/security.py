"""
Security service for Standalone Native Authentication.

Handles PBKDF2 password hashing and JWT token issuance and decoding.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from uuid import uuid4
import jwt
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password as django_check_password


class SecurityError(Exception):
    """Base exception for authentication and token validation errors."""
    pass


def get_jwt_secret() -> str:
    """Returns the secret key used for signing JWT tokens."""
    return getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)


def hash_password(raw_password: str) -> str:
    """Hashes a plaintext password using Django's PBKDF2-SHA256 hasher."""
    if not raw_password:
        raise ValueError("Password cannot be empty")
    return make_password(raw_password)


def verify_password(raw_password: str, hashed_password: str | None) -> bool:
    """Verifies a plaintext password against a PBKDF2-SHA256 hash."""
    if not raw_password or not hashed_password:
        return False
    return django_check_password(raw_password, hashed_password)


def create_access_token(payload: Dict[str, Any], expires_in_minutes: int = 60) -> str:
    """
    Creates a signed JWT access token with expiration and issue timestamps.
    """
    now = datetime.now(timezone.utc)
    token_payload = payload.copy()
    token_payload["iat"] = int(now.timestamp())
    token_payload["exp"] = int((now + timedelta(minutes=expires_in_minutes)).timestamp())
    token_payload.setdefault("type", "access")

    secret = get_jwt_secret()
    return jwt.encode(token_payload, secret, algorithm="HS256")


def create_refresh_token(payload: Dict[str, Any], expires_in_days: int = 30) -> str:
    """
    Creates a signed long-lived JWT refresh token.
    """
    now = datetime.now(timezone.utc)
    token_payload = payload.copy()
    token_payload["iat"] = int(now.timestamp())
    token_payload["exp"] = int((now + timedelta(days=expires_in_days)).timestamp())
    token_payload["type"] = "refresh"
    token_payload["jti"] = str(uuid4())

    secret = get_jwt_secret()
    return jwt.encode(token_payload, secret, algorithm="HS256")


def decode_token(token: str, expected_type: str | None = None) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token. Raises SecurityError on failure.
    """
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if expected_type and payload.get("type") != expected_type:
            raise SecurityError("Tipo de token inválido")
        return payload
    except jwt.ExpiredSignatureError as e:
        raise SecurityError("Token expirado") from e
    except jwt.InvalidTokenError as e:
        raise SecurityError("Token inválido") from e
