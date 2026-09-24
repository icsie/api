"""FastAPI 應用程式的主要入口。

這個檔案負責建立 FastAPI app、註冊各個 router，並放置仍屬於
示範用途的簡單 endpoint。實際的 notes API 則放在 routers 模組中，
讓不同功能可以分開維護。
"""

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from app.core.static_files import HtmlCssOnlyStaticFiles
from app.routers.notes import router as notes_router

# 建立整個 API 應用程式。FastAPI 會使用這個物件註冊路由與產生文件。
app = FastAPI(
    title="My Backend API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    root_path="/s115999999",
)

# 統一管理所有 API 路由，讓每個 API path 都以 /api 開頭。
api_router = APIRouter(prefix="/api")

# 將 notes router 加入 API router，完整路徑會是 /api/note/{note_id}。
api_router.include_router(notes_router)

# 將專案根目錄下的 public 資料夾作為 HTTP 靜態檔案根目錄。
# html=True 會讓 GET / 自動回傳靜態資料夾中的 index.html。
public_directory = "C:\\code\\web\\webui"


class Item(BaseModel):
    """POST /api/items 使用的請求與回應資料格式。"""

    name: str
    price: float


@api_router.get("/health")
def health_check():
    """提供簡單的服務健康檢查。"""

    return {"status": "ok"}


@api_router.get("/version")
def version():
    """回傳目前 API 版本。"""

    return {"version": "0.1.0"}


@api_router.post("/items", response_model=Item)
def create_item(item: Item) -> Item:
    """驗證並原樣回傳收到的 item，目前不會寫入資料庫。"""

    return item


# 將統一的 API router 掛入 app。
app.include_router(api_router)

# 靜態檔案 mount 放在最後，避免網站資料夾攔截 API 路徑。
app.mount(
    "/",
    HtmlCssOnlyStaticFiles(directory=public_directory, html=True),
    name="public",
)