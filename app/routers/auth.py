"""Google OAuth login and authenticated profile routes."""

import os
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
import psycopg

from app.core.db import get_db_connection
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    JWT_SECRET_KEY,
    SESSION_SECRET_KEY,
    create_access_token,
    get_current_member,
)
from app.repositories.member import upsert_google_member

router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
)


def ensure_oauth_configuration() -> str:
    """Require explicit secrets and a registered Google callback URL."""

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not all((client_id, client_secret, redirect_uri, JWT_SECRET_KEY, SESSION_SECRET_KEY)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )
    if redirect_uri is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )
    return redirect_uri


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    """Start Google's OpenID Connect flow and validate its state on callback."""

    redirect_uri = ensure_oauth_configuration()
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", include_in_schema=False)
@router.get("/callback/", include_in_schema=False)
@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    request: Request,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> RedirectResponse:
    """Verify Google's response, persist the profile, and set a JWT cookie."""

    ensure_oauth_configuration()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed",
        ) from error

    user_info: dict[str, Any] | None = token.get("userinfo")
    if (
        not user_info
        or not user_info.get("sub")
        or not user_info.get("email")
        or user_info.get("email_verified") is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account does not have a verified email address",
        )

    member = upsert_google_member(
        connection,
        str(user_info["sub"]),
        str(user_info["email"]),
        user_info.get("name"),
        user_info.get("picture"),
    )
    response = RedirectResponse(
        url=os.getenv("AUTH_SUCCESS_REDIRECT_URL", "/"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(member["id"]),
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me")
def read_current_member(
    member: dict[str, Any] = Depends(get_current_member),
) -> dict[str, str | None]:
    """Return the signed-in profile expected by the frontend."""

    return {"name": member["name"], "email": member["email"], "picture": member["picture"]}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    """Clear the browser's JWT cookie; safe to call when already logged out."""

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
    )
    return response