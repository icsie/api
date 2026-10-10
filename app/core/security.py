"""Google login settings and database-backed JWT authentication."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import get_db_connection
from app.repositories.member import get_member_by_id

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "wke-api"
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "28800"))
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
AUTH_COOKIE_NAME = "access_token"

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(member_id: int) -> str:
    """Sign a short-lived JWT identifying a persisted member."""

    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(member_id),
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def get_authenticated_member_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Validate a bearer token or HttpOnly cookie before opening a DB connection."""

    token = credentials.credentials if credentials else request.cookies.get(AUTH_COOKIE_NAME)
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token or not JWT_SECRET_KEY:
        raise unauthorized

    try:
        claims = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "iss", "iat", "exp"]},
        )
        member_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    return member_id


def get_current_member(
    member_id: int = Depends(get_authenticated_member_id),
    connection: psycopg.Connection = Depends(get_db_connection),
) -> dict[str, Any]:
    """Resolve a verified JWT subject to a member that still exists in the DB."""

    member = get_member_by_id(connection, member_id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return member