"""notes API 的 HTTP 路由層。

這一層接收 URL 參數、取得資料庫 dependency、呼叫 repository，
再把資料庫結果轉換成適合 HTTP 回應的格式。
"""

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db_connection
from app.repositories.notes import get_note_by_id
from app.schemas.notes import NoteResponse

# prefix 會加在本模組所有路由前面，因此完整路徑是 /note/{note_id}。
router = APIRouter(prefix="/note", tags=["notes"])


@router.get("/{note_id}", response_model=NoteResponse)
def read_note(
    note_id: int,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> NoteResponse:
    """依照 URL 中的 id 回傳一筆 note。"""

    # Depends 會由 FastAPI 自動提供 connection，request 結束後也會清理。
    note = get_note_by_id(connection, note_id)
    if note is None:
        # 將 repository 的「找不到資料」轉換成 HTTP 404。
        raise HTTPException(status_code=404, detail="Note not found")

    # **note 將 dictionary 欄位展開成 NoteResponse 的同名欄位。
    return NoteResponse(**note)