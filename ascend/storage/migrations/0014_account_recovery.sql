CREATE TABLE account_recovery (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
