"""Database queries for class-object relationships."""

from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def get_co_by_cid(
    connection: psycopg.Connection,
    cid: int,
) -> list[dict[str, Any]]:
    """Return rows from the public view named by the class description."""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT des FROM public.eer_subclass WHERE cid = %s",
            (cid,),
        )
        class_row = cursor.fetchone()
        if class_row is None:
            return []

        view_name = class_row["des"]
        if not isinstance(view_name, str) or not view_name.strip():
            raise RuntimeError(f"Class {cid} does not have a view name in des")

        view_name = view_name.strip()
        cursor.execute(
            """
            SELECT relation.relname
            FROM pg_catalog.pg_class AS relation
            JOIN pg_catalog.pg_namespace AS namespace
                ON namespace.oid = relation.relnamespace
            WHERE namespace.nspname = %s
                AND relation.relkind IN ('v', 'm')
                AND relation.relname = ANY(%s)
            ORDER BY (relation.relname = %s) DESC
            LIMIT 1
            """,
            ("public", [view_name, view_name.lower()], view_name),
        )
        relation = cursor.fetchone()
        if relation is None:
            raise RuntimeError(
                f"View public.{view_name} configured for class {cid} does not exist"
            )

        query = sql.SQL("SELECT * FROM {} WHERE cid = %s").format(
            sql.Identifier("public", relation["relname"])
        )
        cursor.execute(query, (cid,))
        return cursor.fetchall()
