"""
NOA SQL Scanner Web - Authentication Module
"""

import hashlib
import secrets

def hash_password(password):
    """Hash password with SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(input_password, stored_hash):
    """Verify password"""
    return hash_password(input_password) == stored_hash

def generate_session_token():
    """Generate secure session token"""
    return secrets.token_urlsafe(32)
