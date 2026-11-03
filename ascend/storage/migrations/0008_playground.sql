CREATE TABLE activity_runs (
    user_id INTEGER NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    kind TEXT NOT NULL,
    role TEXT NOT NULL,
    family TEXT NOT NULL,
    reward_key TEXT NOT NULL,
    fixture_key TEXT NOT NULL,
    fixture TEXT NOT NULL,
    readiness TEXT NOT NULL,
    work TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('active','saved','passed','ended')),
    checks INTEGER NOT NULL DEFAULT 0,
    hints INTEGER NOT NULL DEFAULT 0,
    revealed INTEGER NOT NULL DEFAULT 0,
    familiar INTEGER NOT NULL DEFAULT 0,
    result TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id,id)
);
CREATE UNIQUE INDEX activity_foreground ON activity_runs(user_id) WHERE status='active';
CREATE INDEX activity_history ON activity_runs(user_id,activity_id,created_at);
CREATE TABLE activity_rewards (
    user_id INTEGER NOT NULL REFERENCES users(id),
    reward_key TEXT NOT NULL,
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    day TEXT NOT NULL,
    points INTEGER NOT NULL,
    PRIMARY KEY(user_id,reward_key),
    FOREIGN KEY(user_id,run_id) REFERENCES activity_runs(user_id,id)
);
CREATE TABLE activity_evidence (
    user_id INTEGER NOT NULL REFERENCES users(id),
    run_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    fixture_key TEXT NOT NULL,
    outcome TEXT NOT NULL,
    independent INTEGER NOT NULL,
    transfer INTEGER NOT NULL,
    day TEXT NOT NULL,
    PRIMARY KEY(user_id,run_id,skill),
    FOREIGN KEY(user_id,run_id) REFERENCES activity_runs(user_id,id)
);
CREATE TABLE activity_bookmarks (
    user_id INTEGER NOT NULL REFERENCES users(id),
    activity_id TEXT NOT NULL,
    PRIMARY KEY(user_id,activity_id)
);
ALTER TABLE entries ADD COLUMN activity_run_id TEXT;
CREATE UNIQUE INDEX activity_habit_event ON entries(user_id,activity_run_id,day) WHERE activity_run_id IS NOT NULL;
CREATE TRIGGER activity_insert_guard BEFORE INSERT ON activity_runs
WHEN NEW.status='active' AND EXISTS(SELECT 1 FROM task_sessions WHERE user_id=NEW.user_id AND status='running')
BEGIN SELECT RAISE(ABORT, 'End the scored track attempt before starting an activity'); END;
CREATE TRIGGER activity_update_guard BEFORE UPDATE OF status ON activity_runs
WHEN NEW.status='active' AND EXISTS(SELECT 1 FROM task_sessions WHERE user_id=NEW.user_id AND status='running')
BEGIN SELECT RAISE(ABORT, 'End the scored track attempt before resuming an activity'); END;
CREATE TRIGGER track_insert_guard BEFORE INSERT ON task_sessions
WHEN NEW.status='running' AND EXISTS(SELECT 1 FROM activity_runs WHERE user_id=NEW.user_id AND status='active')
BEGIN SELECT RAISE(ABORT, 'Save the Playground activity before starting a track session'); END;
CREATE TRIGGER track_update_guard BEFORE UPDATE OF status ON task_sessions
WHEN NEW.status='running' AND EXISTS(SELECT 1 FROM activity_runs WHERE user_id=NEW.user_id AND status='active')
BEGIN SELECT RAISE(ABORT, 'Save the Playground activity before resuming a track session'); END;
