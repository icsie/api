# Google OAuth / JWT 登入紀錄

本文整理目前 FastAPI 專案的 Google 登入流程、主要程式碼、PostgreSQL schema、部署設定與本次對話中的除錯結果。密碼、OAuth client secret、JWT secret 等值一律不記錄在本文。

## 目前狀態摘要

- 前端進入點：`GET /api/auth/google/login`。
- 登出端點：`POST /api/auth/logout`，回傳 204 並使目前瀏覽器的 JWT cookie 失效。
- 正式 Google callback：`GET /api/auth/google/callback`。Google Cloud Console 與 `GOOGLE_REDIRECT_URI` 必須逐字相同；目前使用公開 HTTPS host 與 `/s115999999` 部署前綴，路徑尾端**不加斜線**。
- callback 別名仍存在：`/api/auth/callback`、`/api/auth/callback/`。正式設定仍建議統一使用上面的 `/google/callback` 路徑。
- 登入成功後，後端以 HttpOnly cookie 傳 JWT；`GET /api/auth/me` 回傳資料庫中的 member `id` 與登入者資料，前端以此 `id` 呼叫 `/api/subclass/pcid/{id}`。
- `/api/note` 的 CRUD 路由維持公開；`/api/subclass` 要求有效 OAuth 登入 JWT。兩者仍需 PostgreSQL 可用且資料庫帳號具備查詢權限。`/api/auth/me` 也要求有效登入。
- DB 連線及 `member` 表曾確認存在，但當時 API 使用的 `dev_user` 對 table 和 identity sequence 沒有權限。最新 SQL 已加入 GRANT；需以具備授權權限的 DB role 執行後才會生效。
- **目前 `psql/createtables.sql` 檔尾有未完成的 `SELECT *`。先修正或移除該行，再執行 SQL；不可直接執行整份腳本，因為前段會 DROP 並重建 `notes`。**

## 程式碼分工

| 檔案 | 責任與重要程式碼 |
| --- | --- |
| [app/main.py](app/main.py) | 建立 FastAPI app，設定 `root_path="/s115999999"`，掛載 `SessionMiddleware`，將 auth router 加到 `/api` router。OAuth state 存在短效 session cookie；靜態檔案最後才 mount，避免攔截 API。 |
| [app/routers/auth.py](app/routers/auth.py) | Authlib 註冊 Google OpenID Connect metadata 及 `openid email profile` scope。`google_login()` 轉址到 Google；`google_callback()` 驗證授權回應、檢查 `sub/email/email_verified`、upsert member、簽發 JWT cookie；`read_current_member()` 提供前端 profile。 |
| [app/core/security.py](app/core/security.py) | 建立 HS256 JWT，驗證 cookie 或 Bearer token 的簽章、issuer、必要 claims 與期限，再以 `sub` 作 member id。先驗 JWT、後取 DB，確保未登入請求可以直接得到 401。 |
| [app/repositories/member.py](app/repositories/member.py) | 使用參數化 SQL 將 Google profile 寫入 `member`；`google_sub` 衝突時更新 profile。另依 JWT member id 查詢仍存在且已驗證的 member。 |
| [app/routers/notes.py](app/routers/notes.py) | 公開 notes CRUD 路由；使用 `get_db_connection` 存取資料，但不要求 OAuth/JWT。 |
| [app/routers/subclass.py](app/routers/subclass.py) | 使用 router-level `Depends(get_current_member)` 保護 subclass GET 路由；有效 JWT 與 DB member 均需存在。 |
| [app/core/db.py](app/core/db.py) | 由 `DATABASE_URL` 建立 psycopg connection，FastAPI request 結束時關閉 connection。 |
| [psql/createtables.sql](psql/createtables.sql) | 定義 `member` 表及 `dev_user` 的 table/identity sequence 權限。腳本也會刪除並重建 notes，請先修復檔尾未完成 SQL，並避免在有 notes 資料的正式 DB 執行整份腳本。 |
| [requirements.txt](requirements.txt) | 登入依賴包含 Authlib、PyJWT、httpx、itsdangerous；`itsdangerous` 是 Starlette SessionMiddleware 簽署 session 所需。 |
| [.env.example](.env.example) | 設定名稱範本。正式 secret 只放在未提交的 `.env` 或部署平台 secret store，不要把真實憑證寫進此範例或文件。 |

## 登入流程

```text
Browser
	-> GET /api/auth/google/login
	-> Authlib 建立 OAuth state，導向 Google
	-> Google 驗證使用者，導回 GOOGLE_REDIRECT_URI
	-> 後端檢查 state、交換 authorization code、驗證 OIDC userinfo
	-> 確認 sub、email、email_verified=true
	-> upsert public.member
	-> 簽發 JWT，寫入 HttpOnly cookie
	-> 303 redirect 到 AUTH_SUCCESS_REDIRECT_URL
	-> 前端 GET /api/auth/me（same-origin cookie）
	-> JWT 驗證後，以 member id 查 DB，再回傳 name/email/picture
	-> POST /api/auth/logout 刪除瀏覽器 JWT cookie
```

### Google OAuth / OIDC

前端只導向 login endpoint，不直接處理 Google client secret。Authlib 使用 Google 的 OpenID Connect discovery 文件取得授權與 token endpoint。`state` 用來關聯發起與返回的 OAuth 流程並降低 CSRF 風險；FastAPI 的 `SessionMiddleware` 透過 `SESSION_SECRET_KEY` 簽署 session cookie。callback 必須由 login 流程導入，直接在網址列打開 callback 沒有有效 state/code，不能當作登入測試。

後端不以 email 當 Google 唯一識別，而使用 OIDC 的 `sub`（Google account subject）作為 `google_sub` unique key。email 必須存在且 `email_verified` 為 true 才接受。姓名、圖片可能不存在，所以 schema 欄位允許 NULL。

### JWT 與後續 API

JWT claims 包含：

| Claim | 用途 |
| --- | --- |
| `sub` | 本系統 `member.id`，不是 email 或 Google subject。 |
| `iss` | 固定 issuer `wke-api`，防止接受其他 issuer 的 token。 |
| `iat` | 簽發時間。 |
| `exp` | 到期時間，預設由 `ACCESS_TOKEN_EXPIRE_SECONDS=28800` 控制。 |

`POST /api/auth/logout` 不要求登入，因此重複呼叫也會成功；它以相同 cookie name、path、Secure、HttpOnly 和 SameSite 屬性回傳過期 cookie，瀏覽器會移除目前保存的 access token。此設計適用前端的 HttpOnly cookie session。JWT 本身是 stateless：若 client 曾把 token 複製到 `Authorization: Bearer` 或其他裝置，清除瀏覽器 cookie 不會撤銷該 token，它仍可用到 `exp`。若需求是立即撤銷所有複製出去的 token，需另加 DB token revocation/JTI 或 member token-version 機制。

演算法固定為 HS256，不接受 token 自行指定其他演算法。瀏覽器使用 `HttpOnly` cookie，JavaScript 無法直接讀取；同時可讓 API client 以 `Authorization: Bearer <JWT>` 傳送。每個受保護 request 除了驗簽與期限，也會以 `sub` 查詢 DB，因此刪除/停用帳號後，舊 token 不會只靠簽章繼續被接受。

生產環境設定 `AUTH_COOKIE_SECURE=true`，只透過 HTTPS 傳送 cookie；`SameSite=Lax` 適用一般 top-level Google redirect callback。`SESSION_SECRET_KEY` 和 `JWT_SECRET_KEY` 必須是彼此不同、不可預測的長隨機值。程式中的 development fallback 不可用於正式部署。

## 資料表與權限

`member` 的重要欄位：

| 欄位 | 說明 |
| --- | --- |
| `id` | 本系統 identity primary key，JWT 的 `sub`。 |
| `google_sub` | Google OIDC 穩定識別值，unique；用於 login upsert。 |
| `email` | Google 回傳且已驗證的 email。 |
| `name`, `picture` | 前端 profile 欄位，可為 NULL。 |
| `email_verified` | 只有 Google 回報已驗證時才可登入。 |
| `created_at`, `updated_at` | 建立與 profile 更新時間。 |

Repository 使用 `INSERT ... ON CONFLICT (google_sub) DO UPDATE`，所以首次登入新增會員，後續登入更新 Google profile，不會因同一帳號重複建立資料。資料庫 role 至少需要 member 的 SELECT/INSERT/UPDATE，以及 identity sequence 的 USAGE/SELECT。最新 SQL 內的授權概念如下：

```sql
GRANT SELECT, INSERT, UPDATE ON TABLE public.member TO dev_user;
GRANT USAGE, SELECT ON SEQUENCE public.member_id_seq TO dev_user;
```

這些 GRANT 必須由 table/sequence owner 或有授權權限的管理角色執行。修改 SQL 檔本身不會改變已存在資料庫的權限。若正式環境的 API role 不是 `dev_user`，應把 `TO` 後面的角色換成實際 `DATABASE_URL` 使用者。

## 部署設定

正式環境的 OAuth callback URI 必須在 Google Cloud Console 的 OAuth 2.0 Web application client 中登記，且下列值要完全一致：

```text
Google Console Authorized redirect URI
GOOGLE_REDIRECT_URI
https://demo.wke.csie.ncnu.edu.tw/s115999999/api/auth/google/callback
```

scheme、host、deployment prefix、path 及結尾斜線都是比對的一部分。`/callback`、`/google/callback`、是否有尾端 `/` 是不同 URI。使用者瀏覽器在 `/s115999999/` 下方，但反向代理會移除部署前綴後轉送到 Uvicorn；`root_path` 負責告知 FastAPI 外部部署前綴。Google 仍要登記外部瀏覽器可到達的完整 HTTPS URI。

認證相關環境變數：

| 變數 | 用途 |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Google OAuth Web client ID。 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret；僅後端使用。 |
| `GOOGLE_REDIRECT_URI` | 完全匹配 Google Console 設定的 callback URL。 |
| `JWT_SECRET_KEY` | HS256 access token 簽章密鑰。 |
| `SESSION_SECRET_KEY` | OAuth state session cookie 簽章密鑰，需與 JWT key 不同。 |
| `AUTH_COOKIE_SECURE` | HTTPS 部署設為 `true`；僅本機 HTTP 開發才設 `false`。 |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | JWT 有效秒數。 |
| `AUTH_SUCCESS_REDIRECT_URL` | callback 登入完成後的前端 URL，需含 `/s115999999/`。 |

改動 `.env` 後需重啟 Uvicorn，因為 OAuth client 在模組載入時讀取設定。若 callback 已經失敗，請重新從 login endpoint 發起一次流程，讓新的 state/code 配對完整。

## 本次 Debug 時序

### 1. 找出前端契約

FastAPI workspace 自己的 `public/index.html` 是簡單占位頁；實際網站設定在外部 `C:\code\web\webui`。檢查實際前端後確認：登入連結指向 `/api/auth/google/login`，profile loader 使用 same-origin `GET /api/auth/me`，遇到 401 就維持登入按鈕。故後端採瀏覽器 redirect + cookie，而不是要求前端傳 Google ID token JSON。

### 2. Callback 路徑回 404

曾直接測試 `/s115999999/api/auth/callback/`，回應 `{"detail":"Not Found"}`。當時只有 `/api/auth/google/callback`，路徑確實不一致；後端增加 `/api/auth/callback` 和 `/api/auth/callback/` alias。Google Console 後來確認登記的是 `/api/auth/google/callback`，因此正式 `GOOGLE_REDIRECT_URI` 應採 canonical `/google/callback`，不要為了 alias 把 Console callback 改成另一條路徑。

### 3. Google 回報 request invalid

檢查 `.env` 發現 callback 值末尾有 `/`，但 Google Console 的 Authorized redirect URI 沒有 `/`。OAuth redirect URI 必須完全相同；已將 `.env` 改為無尾斜線的 canonical URL。透過 TestClient 呼叫 login endpoint，從回應 Location 的 query string 取出 `redirect_uri`，實際比對結果與 Console URL 相同。這證明後端送出的值正確，但仍需在部署伺服器重啟後從 login endpoint 重跑整個 OAuth 流程。

### 4. callback 直接開啟與匿名 `/me`

callback URL 直接在瀏覽器開啟時沒有 Google 返回的有效 state/code，不代表 OAuth 流程失敗；callback 應由 `/google/login` 開始。另一個測試發現未登入 `/me` 在 DB dependency 先連線且 DB 不可用時可能回 500。將 security dependency 拆成「先驗 JWT、再查 DB」兩段後，匿名請求可先回 401，不需開 DB connection。已用 TestClient 驗證無 DB 時仍為 401。

### 5. OAuth callback 回 500：確認資料庫權限

使用當時 `.env` 的資料庫設定做唯讀檢查，結果如下：

- PostgreSQL connection 成功，`member` 與 `notes` relation 都存在。
- 從 PostgreSQL catalog 讀到的 `member` 欄位與程式預期相符，identity sequence 為 `public.member_id_seq`。
- 目前連線 role 為 `dev_user`，但 `has_table_privilege` 對 member 的 INSERT 和 SELECT 都是 false；`information_schema.columns` 也因權限不足回傳空集合。

因此 callback 在 `upsert_google_member()` 執行 INSERT/ON CONFLICT 時會因 DB 權限不足失敗，這是當時 500 的已驗證根因。最新 `createtables.sql` 加入 member 與 identity sequence GRANT；但**尚未由工具驗證這些 GRANT 已在實際 DB 執行成功**。需用 owner/admin 執行授權，再重新開始 Google login 流程。

### 6. 測試與驗證記錄

- Pylance 對 auth/security/repository/main 等修改檔案沒有診斷。
- `pip check` 無 broken requirements。
- FastAPI smoke test 確認 health 是公開端點，未設定 OAuth 時 login 回 503，匿名 `/me` 與受保護的 notes 回 401。
- 合成 JWT 測試確認 cookie 與 Bearer 都可驗證；錯誤 JWT 回 401。
- OpenAPI 包含 login 與 `/me`，OAuth callback 隱藏於 schema。
- login response 的 `redirect_uri` 曾經實際抽取並確認為 Google Console 設定的精確 URL。
- 曾出現 Starlette 對 `httpx` TestClient 的 deprecation warning；測試仍成功，這不是 callback 500 的原因。
- 真正的 Google-to-Google code exchange 與成功後 member upsert 尚未在本機端到端重跑；需先套用資料庫 GRANT，並在部署環境從 login endpoint 完整測試。

## 安全與維運提醒

- 本次對話曾貼出 Google client secret；應立即在 Google Cloud Console 輪替該 secret，更新部署環境後再撤銷舊值。此文件不保存該值。
- 若 `JWT_SECRET_KEY` 或 `SESSION_SECRET_KEY` 仍是範例 placeholder，請先換成兩個互不相同的高熵隨機值。更換 JWT key 會使既有 JWT 全數失效；更換 session key 會使進行中的 OAuth state session 失效，需要重新登入。
- 不要把 `.env`、OAuth secrets、JWT、cookie 值或帶 authorization code 的完整 callback URL commit 到 Git、issue 或文件。
- 執行 `psql/createtables.sql` 前先修復目前檔尾未完成的 `SELECT *`。此腳本前段會 `DROP TABLE IF EXISTS notes`，正式 DB 請採非破壞性的 migration 或只執行需要的 member/GRANT SQL。
