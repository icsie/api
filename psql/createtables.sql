DROP TABLE IF EXISTS notes;

CREATE TABLE notes (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	title VARCHAR(200) NOT NULL,
	content TEXT NOT NULL,
	created_at TIMESTaMPTZ NOT NULL DEFAULT CURRENT_TIMESTaMP
);

INSERT INTO notes (title, content)
VALUES
	('First note', 'This is the first note.'),
	('FastAPI setup', 'Connect the API to PostgreSQL.'),
	('Database test', 'Verify that notes can be inserted and queried.');

SELECT id, title, content, created_at
FROM notes
ORDER BY id;

CREATE TABLE IF NOT EXISTS member (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	google_sub TEXT NOT NULL UNIQUE,
	email TEXT NOT NULL,
	name TEXT,
	picture TEXT,
	email_verified BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
GRANT SELECT, INSERT, UPDATE ON TABLE public.member TO dev_user;
GRANT USAGE, SELECT ON SEQUENCE public.member_id_seq TO dev_user;
SELECT * FROM member;

CREATE TABLE IF NOT EXISTS api_sessions (
	id UUID PRIMARY KEY,
	mid INTEGER,
	ip INET,
	started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	ended_at TIMESTAMPTZ
);

CREATE TABLE api_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id UUID REFERENCES api_sessions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip INET,
  method VARCHAR(10) NOT NULL,
  path TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  message TEXT
);

-- 依時間範圍查詢、查看最新紀錄
CREATE INDEX idx_api_logs_created_at ON api_logs (created_at);
-- 查詢某個 session 的紀錄，並依時間排序
CREATE INDEX idx_api_logs_session_created_at ON api_logs (session_id, created_at);
-- 依 IP 查詢，並依時間排序
CREATE INDEX idx_api_logs_ip_created_at ON api_logs (ip, created_at);

-- Session：建立、查詢與更新最後活動時間
GRANT SELECT, INSERT, UPDATE ON TABLE public.api_sessions TO dev_user;
-- Log：新增紀錄
GRANT INSERT ON TABLE public.api_logs TO dev_user;
-- Log 自動編號需要使用 sequence
GRANT USAGE ON SEQUENCE public.api_logs_id_seq TO dev_user;
