"""FastAPI 應用程式的主要入口。

這個檔案負責建立 FastAPI app、註冊各個 router，並放置仍屬於
示範用途的簡單 endpoint。實際的 notes API 則放在 routers 模組中，
讓不同功能可以分開維護。
"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.routers.notes import router as notes_router

# 建立整個 API 應用程式。FastAPI 會使用這個物件註冊路由與產生文件。
app = FastAPI(title="My Backend API")

# 將 notes router 加入主應用程式。完整路徑會是 /note/{note_id}。
app.include_router(notes_router)


class Item(BaseModel):
    """POST /items 使用的請求與回應資料格式。"""

    name: str
    price: float


@app.get("/health")
def health_check():
    """提供簡單的服務健康檢查。"""

    return {"status": "ok"}


@app.get("/version")
def version():
    """回傳目前 API 版本。"""

    return {"version": "0.1.0"}


@app.post("/items", response_model=Item)
def create_item(item: Item) -> Item:
    """驗證並原樣回傳收到的 item，目前不會寫入資料庫。"""

    return item