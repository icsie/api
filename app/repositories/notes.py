"""notes 資料表的資料存取層（repository）。

repository 只負責資料庫查詢，不處理 HTTP status code 或 API response。
這樣 router 可以專注在 HTTP 流程，SQL 也集中在一個地方維護。
"""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def get_note_by_id(connection: psycopg.Connection, note_id: int) -> dict[str, Any] | None:
    """依照 id 查詢一筆 note，找不到時回傳 None。

    dict_row 讓查詢結果使用欄位名稱存取，也能配合
    NoteResponse(**note) 建立 API 回應 schema。
    """

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            # 使用 %s 參數化查詢，避免直接拼接輸入值造成 SQL injection。
            """
            SELECT id, title, content, created_at
            FROM notes
            WHERE id = %s
            """,
            (note_id,),
        )

        # id 是 primary key，最多只會有一筆結果；沒有資料時回傳 None。
        return cursor.fetchone()


def get_notes(connection: psycopg.Connection) -> list[dict[str, Any]]:
    """查詢全部 notes，依 id 遞增排序。"""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT id, title, content, created_at
            FROM notes
            ORDER BY id
            """
        )
        return cursor.fetchall()


def create_note(
    connection: psycopg.Connection,
    title: str,
    content: str,
) -> dict[str, Any]:
    """新增 note，並回傳 PostgreSQL 建立的完整資料。"""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            INSERT INTO notes (title, content)
            VALUES (%s, %s)
            RETURNING id, title, content, created_at
            """,
            (title, content),
        )
        note = cursor.fetchone()
    connection.commit()
    return note


def update_note(
    connection: psycopg.Connection,
    note_id: int,
    title: str,
    content: str,
) -> dict[str, Any] | None:
    """完整更新指定 note；找不到時回傳 None。"""

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            UPDATE notes
            SET title = %s, content = %s
            WHERE id = %s
            RETURNING id, title, content, created_at
            """,
            (title, content, note_id),
        )
        note = cursor.fetchone()
    connection.commit()
    return note


def delete_note(connection: psycopg.Connection, note_id: int) -> bool:
    """刪除指定 note，並回傳是否真的刪除資料。"""

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        deleted = cursor.rowcount > 0
    connection.commit()
    return deleted