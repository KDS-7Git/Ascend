CREATE TABLE practice_rewards (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    activity_key TEXT NOT NULL,
    event_key TEXT NOT NULL,
    source TEXT NOT NULL,
    reference TEXT NOT NULL,
    title TEXT NOT NULL,
    reason TEXT NOT NULL,
    day TEXT NOT NULL,
    earned_at TEXT NOT NULL,
    points INTEGER NOT NULL CHECK(points BETWEEN 0 AND 5),
    UNIQUE(user_id, event_key)
);
CREATE UNIQUE INDEX practice_rewards_daily_activity ON practice_rewards(user_id, activity_key, day) WHERE points > 0;
CREATE INDEX practice_rewards_account_day ON practice_rewards(user_id, day, id);
CREATE INDEX practice_rewards_event ON practice_rewards(user_id, event_key, id);
