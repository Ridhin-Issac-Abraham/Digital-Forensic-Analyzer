INSERT INTO custody_chain (
    evidence_id, 
    evidence_type, 
    action_type, 
    action_timestamp, 
    handler, 
    location, 
    notes
)
SELECT 
    id,
    'file',
    'COLLECT',
    datetime('now'),
    'web_interface',
    'upload_portal',
    'Initial evidence collection'
FROM file_metadata;