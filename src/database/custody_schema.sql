CREATE TABLE IF NOT EXISTS custody_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER,
    evidence_type TEXT,
    action_type TEXT,
    action_timestamp TEXT,
    handler TEXT,
    location TEXT,
    hash_before TEXT,
    hash_after TEXT,
    notes TEXT,
    FOREIGN KEY (evidence_id) REFERENCES file_metadata(id)
);