CREATE TABLE activity_feedback (
    user_id INTEGER NOT NULL REFERENCES users(id),
    run_id TEXT NOT NULL,
    working_minutes INTEGER NOT NULL CHECK(working_minutes BETWEEN 1 AND 1440),
    setup_minutes INTEGER NOT NULL CHECK(setup_minutes BETWEEN 0 AND 1440),
    difficulty TEXT NOT NULL CHECK(difficulty IN ('too-easy','about-right','too-hard')),
    clarity TEXT NOT NULL CHECK(clarity IN ('clear','unclear')),
    repetition TEXT NOT NULL CHECK(repetition IN ('fresh','welcome-review','unwanted-repeat')),
    environment_issue INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id,run_id),
    FOREIGN KEY(user_id,run_id) REFERENCES activity_runs(user_id,id)
);
CREATE TABLE activity_events (
    user_id INTEGER NOT NULL REFERENCES users(id),
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('saved','resumed','returned')),
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id,run_id,kind),
    FOREIGN KEY(user_id,run_id) REFERENCES activity_runs(user_id,id)
);
CREATE TABLE activity_selections (
    user_id INTEGER NOT NULL REFERENCES users(id),
    day TEXT NOT NULL,
    filters TEXT NOT NULL,
    available INTEGER NOT NULL,
    recommended INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id,day,filters)
);
ALTER TABLE activity_runs ADD COLUMN elapsed_seconds REAL NOT NULL DEFAULT 0;
ALTER TABLE activity_runs ADD COLUMN running_since TEXT;
UPDATE activity_runs SET running_since=strftime('%Y-%m-%dT%H:%M:%S+00:00','now') WHERE status='active';
CREATE TABLE activity_tour_history (
    user_id INTEGER NOT NULL REFERENCES users(id),
    skill TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('finished','skipped')),
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id,skill)
);
