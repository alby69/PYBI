"""JWT authentication and user password handling for PyBI."""

from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from typing import Any, Dict, Optional

import jwt

SECRET_KEY = os.environ.get("PYBI_JWT_SECRET") or "pybi-secret-key-change-in-production"
ALGORITHM = "HS256"
DEFAULT_EXPIRATION_MINUTES = 60 * 24  # 24 hours


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a plaintext password using SHA-256 and a salt.

    Args:
        password: Plaintext password.
        salt: Optional hex salt string; generated if omitted.

    Returns:
        str: Salt and hashed password as 'salt$hash'.
    """
    if not salt:
        salt = secrets.token_hex(16)
    salted = f"{salt}{password}".encode("utf-8")
    pwd_hash = hashlib.sha256(salted).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a 'salt$hash' hashed password string.

    Args:
        plain_password: Plaintext password typed by user.
        hashed_password: Stored 'salt$hash' password string.

    Returns:
        bool: True if password matches.
    """
    if "$" not in hashed_password:
        return False
    salt, _ = hashed_password.split("$", 1)
    return hash_password(plain_password, salt=salt) == hashed_password


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token encoding the payload data and expiration time.

    Args:
        data: Payload dict containing claims (e.g. {"sub": username, "role": "admin"}).
        expires_delta: Optional custom token validity duration.

    Returns:
        str: Encoded JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=DEFAULT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.

    Args:
        token: Encoded JWT string.

    Returns:
        Optional[Dict[str, Any]]: Decoded payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


class AuthUser:
    """Dataclass or class representing an authenticated user session."""

    def __init__(self, username: str, role: str = "viewer", email: Optional[str] = None) -> None:
        self.username = username
        self.role = role
        self.email = email

    def to_dict(self) -> Dict[str, Any]:
        return {"username": self.username, "role": self.role, "email": self.email}
