CREATE TABLE lab_runs (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, pack_id TEXT NOT NULL,
 node_id TEXT NOT NULL, fingerprint TEXT NOT NULL, exercise TEXT NOT NULL,
 challenge TEXT NOT NULL, created_at TEXT NOT NULL, passed_at TEXT,
 attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX lab_run_node ON lab_runs(user_id,pack_id,node_id,created_at);
CREATE TABLE task_sessions (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, pack_id TEXT NOT NULL,
 node_id TEXT NOT NULL, title TEXT NOT NULL, budget_seconds INTEGER NOT NULL,
 elapsed_seconds REAL NOT NULL DEFAULT 0, running_since TEXT,
 status TEXT NOT NULL CHECK(status IN ('running','paused','finished')),
 notice INTEGER NOT NULL DEFAULT 0, finished_at TEXT,
 UNIQUE(user_id,pack_id,node_id)
);
CREATE UNIQUE INDEX one_running_session ON task_sessions(user_id) WHERE status='running';
CREATE TABLE xp_awards (
 user_id INTEGER NOT NULL, pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
 points INTEGER NOT NULL CHECK(points BETWEEN 25 AND 100), awarded_at TEXT NOT NULL,
 evidence_kind TEXT NOT NULL, PRIMARY KEY(user_id,pack_id,node_id)
);
