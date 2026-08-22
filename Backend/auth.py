"""
Admin authentication for Willow Health Clinic.

Single admin account, credentials read from environment variables:
  ADMIN_USERNAME       plain text, e.g. "admin"
  ADMIN_PASSWORD_HASH  a bcrypt hash (never store the plain password)
  SECRET_KEY           random string used to sign login tokens

To generate ADMIN_PASSWORD_HASH, run once locally:
    python hash_password.py

Install:
    pip install pyjwt passlib[bcrypt]
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str) -> bool:
    if not ADMIN_PASSWORD_HASH:
        return False
    return pwd_context.verify(plain_password, ADMIN_PASSWORD_HASH)


def create_access_token(username: str) -> str:
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set — cannot issue tokens")
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: protects normal routes via the Authorization header."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return decode_token(credentials.credentials)


def require_admin_from_query_or_header(request: Request) -> str:
    """
    FastAPI dependency for the SSE stream endpoint.

    Browsers' EventSource API cannot send custom headers, so the dashboard
    passes the token as ?token=... on that one route instead. Every other
    route uses the normal Authorization header via require_admin above.
    """
    token = request.query_params.get("token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    return decode_token(token)
