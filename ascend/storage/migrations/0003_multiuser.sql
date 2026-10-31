CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, timezone TEXT NOT NULL DEFAULT 'UTC', created_at TEXT NOT NULL);
INSERT INTO users (id,username,password_hash,timezone,created_at) VALUES (1,'local','!disabled','UTC',strftime('%Y-%m-%dT%H:%M:%SZ','now'));
CREATE TABLE api_tokens (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, label TEXT);
CREATE TABLE node_splits (user_id INTEGER NOT NULL, pack_id TEXT NOT NULL, node_id TEXT NOT NULL, steps TEXT NOT NULL, PRIMARY KEY(user_id,pack_id,node_id));
ALTER TABLE node_state ADD COLUMN revision INTEGER NOT NULL DEFAULT 0;
ALTER TABLE entries ADD COLUMN completion_before TEXT;
ALTER TABLE entries ADD COLUMN completion_revision INTEGER;
