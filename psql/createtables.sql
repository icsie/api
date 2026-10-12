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