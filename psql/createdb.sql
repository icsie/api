CREATE Database FastAPI_dev;
CREATE Member dev_Member WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON Database FastAPI_dev TO dev_Member;

\connect FastAPI_dev
GRANT USAGE, CREATE ON SCHEMA public TO dev_Member; -- public schema建表權限
