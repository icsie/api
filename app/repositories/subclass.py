"""Database queries for subclass data."""

from typing import Any, Literal

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def get_subclasses_by_pcid(
    connection: psycopg.Connection,
    pcid: int,
    order_by: Literal["cid", "n"],
) -> list[dict[str, Any]]:
    """Return subclass rows for a parent class ID, ordered by a supported column."""

    query = sql.SQL(
        "SELECT * FROM eer_subclass WHERE pcid = %s ORDER BY {}"
    ).format(sql.Identifier(order_by))
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, (pcid,))
        return cursor.fetchall()
