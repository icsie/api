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