CREATE TABLE push_subscriptions (user_id INTEGER NOT NULL, endpoint TEXT NOT NULL, subscription TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(user_id,endpoint));
CREATE TABLE telegram_updates (user_id INTEGER NOT NULL, update_id INTEGER NOT NULL, PRIMARY KEY(user_id,update_id));
