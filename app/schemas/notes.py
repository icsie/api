"""notes API 的 Pydantic response schema。

Schema 是 API 資料格式的規格，不是資料庫 model，也不直接執行 SQL。
它負責確認欄位型別，並協助 FastAPI 產生 OpenAPI 文件。
"""

from datetime import datetime

from pydantic import BaseModel


class NoteResponse(BaseModel):
    """GET /api/note/{note_id} 回傳的資料格式。

    欄位名稱對應 notes 資料表及 repository SELECT 的欄位。
    created_at 會以 Python datetime 表示，最後由 FastAPI 序列化成 JSON
    可使用的日期時間字串。
    """

    id: int
    title: str
    content: str
    created_at: datetime