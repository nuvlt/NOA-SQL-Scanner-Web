"""
NOA SQL Scanner Web - Configuration
"""

import os

# Flask Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'NOA-SQL-Scanner-Secret-Key-2025'
    
    # Access Password (hash this!)
    ACCESS_PASSWORD = os.environ.get('ACCESS_PASSWORD') or 'NOA2025SecurePass!'
    
    # Database
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'noa_scanner.db'
    
    # Reports directory
    REPORTS_DIR = os.environ.get('REPORTS_DIR') or 'reports'
    
    # Session timeout (minutes)
    SESSION_TIMEOUT = 60
    
    # Max concurrent scans
    MAX_CONCURRENT_SCANS = 3
    
    # Dork settings
    DORK_MAX_RESULTS = 100
    DORK_RATE_LIMIT = 2  # seconds between requests

# Create reports directory
os.makedirs(Config.REPORTS_DIR, exist_ok=True)
