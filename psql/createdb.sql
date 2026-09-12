CREATE DATABASE fastapi_dev;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE fastapi_dev TO dev_user;

\connect fastapi_dev
GRANT USAGE, CREATE ON SCHEMA public TO dev_user; -- public schema建表權限
