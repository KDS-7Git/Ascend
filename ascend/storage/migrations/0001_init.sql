CREATE TABLE missions (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1,
 title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','done','paused')),
 created_at TEXT NOT NULL, finished_at TEXT, nudge_time TEXT
);
CREATE UNIQUE INDEX one_active_mission ON missions(user_id) WHERE status='active';
CREATE TABLE entries (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1, day TEXT NOT NULL,
 logged_at TEXT NOT NULL, mission_id INTEGER REFERENCES missions(id), learned TEXT NOT NULL,
 next_step TEXT NOT NULL, proof TEXT, minutes INTEGER CHECK(minutes > 0)
);
CREATE INDEX idx_entries_day ON entries(user_id, day);
CREATE TABLE parked (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, note TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE settings (user_id INTEGER NOT NULL DEFAULT 1, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(user_id, key));
CREATE TABLE audit (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
