CREATE TABLE packs (
 user_id INTEGER NOT NULL DEFAULT 1, id TEXT NOT NULL, path TEXT NOT NULL, version INTEGER,
 reviewed INTEGER NOT NULL DEFAULT 0, trusted INTEGER NOT NULL DEFAULT 0,
 fingerprint TEXT NOT NULL, PRIMARY KEY(user_id, id)
);
CREATE TABLE node_state (
 user_id INTEGER NOT NULL DEFAULT 1, pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','done','skipped')),
 done_at TEXT, evidence TEXT, how TEXT, PRIMARY KEY(user_id, pack_id, node_id)
);
ALTER TABLE entries ADD COLUMN node_id TEXT;
ALTER TABLE entries ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE entries ADD COLUMN complete INTEGER NOT NULL DEFAULT 0;
ALTER TABLE missions ADD COLUMN pack_id TEXT;
CREATE TABLE level_unlocks (user_id INTEGER NOT NULL DEFAULT 1, pack_id TEXT NOT NULL, level_id TEXT NOT NULL, PRIMARY KEY(user_id, pack_id, level_id));
CREATE TABLE evidence_log (user_id INTEGER NOT NULL DEFAULT 1, pack_id TEXT NOT NULL, node_id TEXT NOT NULL, evidence_time TEXT NOT NULL, PRIMARY KEY(user_id, pack_id, node_id, evidence_time));
