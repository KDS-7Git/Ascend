CREATE TABLE node_checkpoints (
    user_id INTEGER NOT NULL REFERENCES users(id),
    pack_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    definition TEXT NOT NULL,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id,pack_id,node_id,checkpoint_id)
);
