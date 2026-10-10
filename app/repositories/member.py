"""Database access for Google-authenticated members."""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def upsert_google_member(
    connection: psycopg.Connection,
    google_sub: str,
    email: str,
    name: str | None,
    picture: str | None,
) -> dict[str, Any]:
    """Insert a Google member or refresh their profile on the next login."""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            INSERT INTO member (google_sub, email, name, picture, email_verified)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (google_sub) DO UPDATE
            SET email = EXCLUDED.email,
                name = EXCLUDED.name,
                picture = EXCLUDED.picture,
                email_verified = TRUE,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, google_sub, email, name, picture, email_verified
            """,
            (google_sub, email, name, picture),
        )
        member = cursor.fetchone()
    if member is None:
        raise RuntimeError("Google member upsert did not return a row")
    connection.commit()
    return member


def get_member_by_id(connection: psycopg.Connection, member_id: int) -> dict[str, Any] | None:
    """Return a member referenced by a verified JWT, if it still exists."""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT id, google_sub, email, name, picture, email_verified
            FROM member
            WHERE id = %s AND email_verified = TRUE
            """,
            (member_id,),
        )
        return cursor.fetchone()