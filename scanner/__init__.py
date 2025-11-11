"""
NOA SQL Scanner - Automated SQL Injection Vulnerability Scanner

A comprehensive tool for detecting SQL injection vulnerabilities in web applications.
Supports MySQL and PostgreSQL databases with multiple injection techniques.

Author: N. Onur Altaş
License: MIT
Version: 1.9.0.3
"""

__version__ = "1.9.0.3"
__author__ = "Nüvit Onur Altaş"
__license__ = "MIT"

from .crawler import Crawler
from .scanner import SQLScanner
from .detector import VulnerabilityDetector
from .reporter import Reporter

__all__ = [
    'Crawler',
    'SQLScanner',
    'VulnerabilityDetector',
    'Reporter',
]
