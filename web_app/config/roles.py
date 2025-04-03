ROLE_PERMISSIONS = {
    'admin': [
        'manage_users',
        'view_all_evidence',
        'collect_evidence',
        'analyze_evidence',
        'generate_reports',
        'view_logs'
    ],
    'investigator': [
        'collect_evidence',
        'view_assigned_evidence',
        'analyze_evidence',
        'generate_reports'
    ],
    'analyst': [
        'view_assigned_evidence',
        'analyze_evidence'
    ]
}