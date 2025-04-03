CREATE TABLE IF NOT EXISTS image_metadata (
    file_id INTEGER PRIMARY KEY,
    width INTEGER,
    height INTEGER,
    format TEXT,
    mode TEXT,
    is_animated BOOLEAN,
    frames INTEGER,
    exif_data TEXT,
    FOREIGN KEY (file_id) REFERENCES file_metadata(id)
);