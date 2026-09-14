"""Password hashing + bearer-token auth.

Passwords: PBKDF2-HMAC-SHA256 via stdlib hashlib (no extra dependency).
Tokens: opaque random strings kept in the store's in-memory session map.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import ApiError, User, UserInDB

_ITERATIONS = 210_000

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2-sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, iters, salt_hex, dk_hex = hashed.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2-sha256":
        return False
    try:
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters)
        )
    except ValueError:
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_token() -> str:
    return secrets.token_urlsafe(32)


def is_devops(user: User | UserInDB) -> bool:
    return user.role == "devops"


async def _credentials(request: Request) -> str:
    creds: HTTPAuthorizationCredentials | None = await bearer_scheme(request)
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise ApiError(401, "Not authenticated. Log in to get a bearer token.")
    return creds.credentials


async def get_current_user(request: Request) -> User:
    """FastAPI dependency: resolve the bearer token to a public User."""
    token = await _credentials(request)
    store = request.app.state.store
    user = store.get_user_by_token(token)
    if user is None:
        raise ApiError(401, "Invalid or expired token.")
    return user.public()


async def get_current_token(request: Request) -> str:
    """FastAPI dependency: the raw bearer token (for logout)."""
    await get_current_user(request)  # validates the token first
    return await _credentials(request)
