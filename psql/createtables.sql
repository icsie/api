DROP TABLE IF EXISTS notes;

CREATE TABLE notes (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	title VARCHAR(200) NOT NULL,
	content TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO notes (title, content)
VALUES
	('First note', 'This is the first note.'),
	('FastAPI setup', 'Connect the API to PostgreSQL.'),
	('Database test', 'Verify that notes can be inserted and queried.');

SELECT id, title, content, created_at
FROM notes
ORDER BY id;
