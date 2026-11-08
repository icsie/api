"""API session tracking and asynchronous PostgreSQL request logging."""

import asyncio
import logging
import os
from ipaddress import ip_address
from uuid import UUID, uuid4

import psycopg
from itsdangerous import BadSignature, TimestampSigner
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS, AUTH_COOKIE_SECURE, SESSION_SECRET_KEY,
)

logger = logging.getLogger(__name__)
SESSION_COOKIE = "api_session"


async def write_request(session_id, mid, ip, method, path, status_code, message, ended):
    """Commit the session and its log together; roll back both on failure."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    async with await psycopg.AsyncConnection.connect(database_url, connect_timeout=3) as conn:
        cursor = await conn.execute(
            """
            INSERT INTO api_sessions (id, mid, ip, ended_at)
            VALUES (%s, %s, %s, CASE WHEN %s THEN NOW() END)
            ON CONFLICT (id) DO UPDATE SET
                mid = COALESCE(EXCLUDED.mid, api_sessions.mid),
                last_seen_at = NOW(),
                ended_at = EXCLUDED.ended_at
            WHERE api_sessions.ended_at IS NULL
            RETURNING id
            """,
            (session_id, mid, ip, ended),
        )
        session = await cursor.fetchone()
        await conn.execute(
            """INSERT INTO api_logs
               (session_id, ip, method, path, status_code, message)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (session[0] if session else None, ip, method, path, status_code, message),
        )


class RequestLoggingMiddleware:
    """Pure ASGI middleware: send the response before awaiting bounded DB I/O."""

    def __init__(self, app):
        self.app = app
        # Missing secrets must never result in forgeable persistent session cookies.
        self.signer = TimestampSigner(SESSION_SECRET_KEY, salt="api-session") if SESSION_SECRET_KEY else None

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == "/api" or path.startswith("/api/")):
            return await self.app(scope, receive, send)

        request = Request(scope)
        session_id = uuid4()
        if self.signer:
            try:
                session_id = UUID(self.signer.unsign(
                    request.cookies.get(SESSION_COOKIE, ""),
                    max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
                ).decode())
            except (BadSignature, ValueError):
                pass
        state = scope.setdefault("state", {})
        state["api_session_id"] = session_id
        try:
            ip = str(ip_address(request.client.host)) if request.client else None
        except ValueError:
            ip = None
        status_code = 500
        started = False
        message = None

        async def send_response(event):
            nonlocal started, status_code
            if event["type"] == "http.response.start":
                started = True
                status_code = event["status"]
                cookie = Response()
                if state.get("api_session_ended"):
                    cookie.delete_cookie(SESSION_COOKIE, secure=AUTH_COOKIE_SECURE, httponly=True, samesite="lax")
                elif self.signer:
                    cookie.set_cookie(
                        SESSION_COOKIE, self.signer.sign(str(session_id)).decode(),
                        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
                        secure=AUTH_COOKIE_SECURE, httponly=True, samesite="lax",
                    )
                event = {**event, "headers": list(event.get("headers", [])) + [
                    header for header in cookie.raw_headers if header[0] == b"set-cookie"
                ]}
            await send(event)

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            logger.exception("Unhandled API error")
            message = "Internal server error"
            if started:
                raise
            await JSONResponse({"detail": message}, status_code=500)(scope, receive, send_response)
        finally:
            # Never store query strings, request bodies, JWTs or raw exception text.
            message = message or state.get("api_error_message")
            if message is None and status_code >= 400:
                message = f"HTTP {status_code}"
            try:
                await asyncio.wait_for(write_request(
                    session_id, state.get("mid"), ip, scope["method"], path,
                    status_code, message, state.get("api_session_ended", False),
                ), timeout=5)
            except Exception:
                logger.exception("Failed to persist API session/log")
