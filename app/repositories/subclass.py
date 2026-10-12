"""Database queries for subclass data."""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def get_subclasses_by_pcid(
    connection: psycopg.Connection,
    pcid: int,
) -> list[dict[str, Any]]:
    """Return all subclass rows for a parent class ID."""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT * FROM eer_subclass WHERE pcid = %s",
            (pcid,),
        )
        return cursor.fetchall()
