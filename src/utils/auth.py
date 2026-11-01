from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import List, Optional

import jwt
from flask import g, jsonify, request

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))


def _hashed(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _load_api_keys() -> dict:
    """
    Load valid API keys from environment variables.
    In production, replace with a DB-backed key store.
    """
    keys: dict = {}
    recruiter_key = os.getenv("RECRUITER_API_KEY")
    admin_key = os.getenv("ADMIN_API_KEY")
    if recruiter_key:
        keys[_hashed(recruiter_key)] = {"role": "recruiter", "user_id": "recruiter"}
    if admin_key:
        keys[_hashed(admin_key)] = {"role": "admin", "user_id": "admin"}
    return keys


def issue_token(api_key: str) -> Optional[str]:
    """Return a signed JWT for a valid API key, or None if the key is invalid."""
    entry = _load_api_keys().get(_hashed(api_key))
    if not entry:
        return None
    payload = {
        "sub": entry["user_id"],
        "role": entry["role"],
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(roles: Optional[List[str]] = None):
    """
    Decorator: require a valid JWT in the Authorization: Bearer header.
    Optionally restrict access to specific roles (e.g. ['admin']).
    If neither RECRUITER_API_KEY nor ADMIN_API_KEY is configured, auth is
    effectively disabled — all requests pass. This allows running the app
    in development without secrets, while enforcing auth in production.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not _load_api_keys():
                # No keys configured — development mode, skip auth.
                g.current_user = {"sub": "anonymous", "role": "recruiter"}
                return f(*args, **kwargs)

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Authorization header missing or malformed"}), 401

            token = auth_header[7:]
            claims = _decode_token(token)
            if claims is None:
                return jsonify({"error": "Invalid or expired token"}), 401

            if roles and claims.get("role") not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403

            g.current_user = claims
            return f(*args, **kwargs)
        return wrapped
    return decorator
