"""資料庫連線管理。

這個模組提供 FastAPI dependency，讓每個 API request 都能取得一個
PostgreSQL connection，並在 request 結束時自動關閉它。
"""

import os
from collections.abc import Generator

import psycopg
from dotenv import load_dotenv

# 從專案根目錄的 .env 載入本機開發設定。
load_dotenv()


def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """提供一個 request 期間使用的 PostgreSQL connection。

    使用 yield 是因為 FastAPI dependency 可以在 yield 前準備資源，
    讓 endpoint 使用；endpoint 完成後，再執行 finally 裡的清理工作。
    """

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # 提前回報設定錯誤，比讓 psycopg 用空值連線更容易理解原因。
        raise RuntimeError("DATABASE_URL is not configured")

    connection = psycopg.connect(database_url)
    try:
        yield connection
    finally:
        # 不論查詢成功或發生例外，都要關閉連線，避免 connection leak。
        connection.close()