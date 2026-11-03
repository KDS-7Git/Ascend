CREATE TABLE external_lab_attempts (
    user_id INTEGER NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    recipe_version TEXT NOT NULL,
    checker_version TEXT NOT NULL,
    fixture_id TEXT NOT NULL,
    nonce_hash TEXT NOT NULL,
    origin TEXT NOT NULL CHECK(origin IN ('online','offline','local')),
    status TEXT NOT NULL CHECK(status IN ('preparing','active','imported','finished','abandoned')),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    result TEXT,
    PRIMARY KEY(user_id,id)
);
CREATE UNIQUE INDEX external_lab_foreground ON external_lab_attempts(user_id) WHERE status IN ('preparing','active');
CREATE TRIGGER external_lab_insert_guard BEFORE INSERT ON external_lab_attempts
WHEN NEW.status IN ('preparing','active') AND (
    EXISTS(SELECT 1 FROM task_sessions WHERE user_id=NEW.user_id AND status='running') OR
    EXISTS(SELECT 1 FROM activity_runs WHERE user_id=NEW.user_id AND status='active'))
BEGIN SELECT RAISE(ABORT, 'Finish the active session before starting a local lab'); END;
CREATE TRIGGER external_lab_update_guard BEFORE UPDATE OF status ON external_lab_attempts
WHEN NEW.status IN ('preparing','active') AND (
    EXISTS(SELECT 1 FROM task_sessions WHERE user_id=NEW.user_id AND status='running') OR
    EXISTS(SELECT 1 FROM activity_runs WHERE user_id=NEW.user_id AND status='active'))
BEGIN SELECT RAISE(ABORT, 'Finish the active session before resuming a local lab'); END;
CREATE TRIGGER external_lab_track_insert_guard BEFORE INSERT ON task_sessions
WHEN NEW.status='running' AND EXISTS(SELECT 1 FROM external_lab_attempts WHERE user_id=NEW.user_id AND status IN ('preparing','active'))
BEGIN SELECT RAISE(ABORT, 'Finish the local lab before starting a track session'); END;
CREATE TRIGGER external_lab_track_update_guard BEFORE UPDATE OF status ON task_sessions
WHEN NEW.status='running' AND EXISTS(SELECT 1 FROM external_lab_attempts WHERE user_id=NEW.user_id AND status IN ('preparing','active'))
BEGIN SELECT RAISE(ABORT, 'Finish the local lab before resuming a track session'); END;
CREATE TRIGGER external_lab_activity_insert_guard BEFORE INSERT ON activity_runs
WHEN NEW.status='active' AND EXISTS(SELECT 1 FROM external_lab_attempts WHERE user_id=NEW.user_id AND status IN ('preparing','active'))
BEGIN SELECT RAISE(ABORT, 'Finish the local lab before starting Playground'); END;
CREATE TRIGGER external_lab_activity_update_guard BEFORE UPDATE OF status ON activity_runs
WHEN NEW.status='active' AND EXISTS(SELECT 1 FROM external_lab_attempts WHERE user_id=NEW.user_id AND status IN ('preparing','active'))
BEGIN SELECT RAISE(ABORT, 'Finish the local lab before resuming Playground'); END;
