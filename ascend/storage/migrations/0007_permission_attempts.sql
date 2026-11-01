CREATE TABLE permission_attempts (
 user_id INTEGER NOT NULL, pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
 run_id TEXT NOT NULL, answers TEXT NOT NULL, challenge TEXT NOT NULL,
 correct_count INTEGER NOT NULL, total_count INTEGER NOT NULL,
 submitted_at TEXT NOT NULL,
 CHECK(total_count > 0 AND correct_count BETWEEN 0 AND total_count),
 PRIMARY KEY(user_id,pack_id,node_id)
);
-- Completed legacy puzzles remain final. Their selected answers were not stored.
INSERT INTO permission_attempts
SELECT r.user_id,r.pack_id,r.node_id,r.id,'{}',r.challenge,
 (SELECT COUNT(*) FROM json_each(r.challenge,'$.expected')),
 (SELECT COUNT(*) FROM json_each(r.challenge,'$.expected')),r.passed_at
FROM lab_runs r
WHERE r.exercise='access-policy' AND r.passed_at IS NOT NULL AND r.rowid=(
 SELECT prior.rowid FROM lab_runs prior
 WHERE prior.user_id=r.user_id AND prior.pack_id=r.pack_id AND prior.node_id=r.node_id
 AND prior.exercise='access-policy' AND prior.passed_at IS NOT NULL
 ORDER BY prior.rowid DESC LIMIT 1
);
-- Retain every existing award exactly; future partial scores may be below 25 XP.
CREATE TABLE xp_awards_scored (
 user_id INTEGER NOT NULL, pack_id TEXT NOT NULL, node_id TEXT NOT NULL,
 points INTEGER NOT NULL CHECK(points BETWEEN 0 AND 100), awarded_at TEXT NOT NULL,
 evidence_kind TEXT NOT NULL, PRIMARY KEY(user_id,pack_id,node_id)
);
INSERT INTO xp_awards_scored SELECT * FROM xp_awards;
DROP TABLE xp_awards;
ALTER TABLE xp_awards_scored RENAME TO xp_awards;
