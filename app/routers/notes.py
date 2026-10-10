"""notes API 的 HTTP 路由層。

這一層接收 URL 參數、取得資料庫 dependency、呼叫 repository，
再把資料庫結果轉換成適合 HTTP 回應的格式。
"""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import get_db_connection
from app.repositories.notes import (
    create_note,
    delete_note,
    get_note_by_id,
    get_notes,
    update_note,
)
from app.schemas.notes import NoteInput, NoteResponse

# prefix 會加在本模組所有路由前面；主 app 再加上 /api，
# 因此完整路徑是 /api/note/{note_id}。
router = APIRouter(prefix="/note", tags=["notes"])


@router.get("", response_model=list[NoteResponse])
def read_notes(
    connection: psycopg.Connection = Depends(get_db_connection),
) -> list[NoteResponse]:
    """以 GET 取得全部 notes。"""

    return [NoteResponse(**note) for note in get_notes(connection)]


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


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note_resource(
    note_data: NoteInput,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> NoteResponse:
    """以 POST 建立一筆 note，成功時回傳 201 Created。"""

    note = create_note(connection, note_data.title, note_data.content)
    return NoteResponse(**note)


@router.put("/{note_id}", response_model=NoteResponse)
def update_note_resource(
    note_id: int,
    note_data: NoteInput,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> NoteResponse:
    """以 PUT 完整更新指定 note；找不到時回傳 404。"""

    note = update_note(connection, note_id, note_data.title, note_data.content)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(**note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_resource(
    note_id: int,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> None:
    """以 DELETE 刪除指定 note；成功時回傳 204 No Content。"""

    if not delete_note(connection, note_id):
        raise HTTPException(status_code=404, detail="Note not found")