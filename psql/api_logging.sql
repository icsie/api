-- Run once as the schema owner. Safe to run again; does not reset existing tables.
CREATE TABLE IF NOT EXISTS public.api_sessions (
    id UUID PRIMARY KEY,
    mid INTEGER,
    ip INET,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS public.api_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID REFERENCES public.api_sessions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip INET,
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON public.api_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_api_logs_session_created_at ON public.api_logs (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_api_logs_ip_created_at ON public.api_logs (ip, created_at);
GRANT SELECT, INSERT, UPDATE ON TABLE public.api_sessions TO dev_user;
GRANT INSERT ON TABLE public.api_logs TO dev_user;
