"""Database queries for class-object relationships."""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def get_co_by_cid(
    connection: psycopg.Connection,
    cid: int,
) -> list[dict[str, Any]]:
    """Return all class-object rows for a class ID."""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT * FROM eer_co WHERE cid = %s",
            (cid,),
        )
        return cursor.fetchall()
