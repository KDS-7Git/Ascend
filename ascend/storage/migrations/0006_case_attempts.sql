CREATE TABLE case_attempts (
 user_id INTEGER NOT NULL, pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
 run_id TEXT NOT NULL, answers TEXT NOT NULL, correct INTEGER NOT NULL CHECK(correct IN (0,1)),
 submitted_at TEXT NOT NULL, challenge TEXT NOT NULL,
 PRIMARY KEY(user_id,pack_id,node_id)
);
-- Preserve recorded legacy outcomes; do not alter progress, awards or timers.
INSERT INTO case_attempts
SELECT r.user_id,r.pack_id,r.node_id,r.id,'{}',r.passed_at IS NOT NULL,
 COALESCE(r.passed_at,r.created_at),r.challenge
FROM lab_runs r
WHERE r.exercise='case' AND r.attempts>0 AND r.rowid=(
 SELECT prior.rowid FROM lab_runs prior
 WHERE prior.user_id=r.user_id AND prior.pack_id=r.pack_id AND prior.node_id=r.node_id
 AND prior.exercise='case' AND prior.attempts>0
 ORDER BY (prior.passed_at IS NOT NULL) DESC, prior.rowid DESC LIMIT 1
);
