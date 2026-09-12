"""手動 PostgreSQL 連線 smoke test。

這不是 API endpoint；直接執行這個檔案時，會確認 .env 的 DATABASE_URL
可以連線，並印出實際連到的資料庫名稱。
"""

import os

import psycopg
from dotenv import load_dotenv

# 載入 DATABASE_URL，讓這個獨立測試使用和 API 相同的設定。
load_dotenv()


def test_connection():
    """建立資料庫連線，印出資料庫名稱後關閉連線。"""

    conn = psycopg.connect(os.getenv("DATABASE_URL"))
    print("連線成功:", conn.info.dbname)
    conn.close()


# 只有直接執行此檔案時才測試連線；被 import 時不會自動連線。
if __name__ == "__main__":
    test_connection()