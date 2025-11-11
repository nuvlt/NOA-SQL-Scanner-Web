"""
NOA SQL Scanner - Configuration & Constants
"""

# Scanning Configuration
MAX_URLS = 500
MAX_CRAWL_DEPTH = 3
RATE_LIMIT_DELAY = 0.5  # seconds between requests
REQUEST_TIMEOUT = 10  # seconds
MAX_THREADS = 10

# Subdomain Discovery
SUBDOMAIN_WORDLIST = [
    'www', 'api', 'admin', 'test', 'dev', 'staging', 'beta',
    'mail', 'ftp', 'blog', 'shop', 'store', 'portal', 'app',
    'dashboard', 'secure', 'vpn', 'remote', 'gateway', 'support',
    'help', 'docs', 'wiki', 'forum', 'community', 'cdn', 'static',
    'assets', 'media', 'images', 'files', 'download', 'upload',
    'demo', 'sandbox', 'qa', 'uat', 'prod', 'production'
]

# User-Agent Rotation for WAF Bypass
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
]

# SQL Injection Detection Patterns
ERROR_PATTERNS = {
    'mysql': [
        r'SQL syntax.*MySQL',
        r'Warning.*mysql_.*',
        r'MySQLSyntaxErrorException',
        r'valid MySQL result',
        r'check the manual that corresponds to your MySQL',
        r'Unknown column.*in.*field list',
        r'MySqlClient\.',
        r'com\.mysql\.jdbc',
        r'Zend_Db_(Adapter|Statement)_Mysqli_Exception',
        r'Pdo[./_\\]Mysql',
        r'MySqlException',
        r'SQLSTATE\[HY000\] \[1045\]',
    ],
    'postgresql': [
        r'PostgreSQL.*ERROR',
        r'Warning.*\Wpg_.*',
        r'valid PostgreSQL result',
        r'Npgsql\.',
        r'PG::SyntaxError',
        r'org\.postgresql\.util\.PSQLException',
        r'ERROR:\s\ssyntax error at or near',
        r'ERROR: parser: parse error at or near',
        r'PostgreSQL query failed',
        r'org\.postgresql\.jdbc',
        r'Pdo[./_\\]Pgsql',
        r'PSQLException',
    ]
}

# Time-based detection threshold (seconds)
TIME_BASED_THRESHOLD = 5

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Banner
BANNER = f"""
{Colors.OKBLUE}
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   ███╗   ██╗ ██████╗  █████╗     ███████╗ ██████╗     ║
║   ████╗  ██║██╔═══██╗██╔══██╗    ██╔════╝██╔═══██╗    ║
║   ██╔██╗ ██║██║   ██║███████║    ███████╗██║   ██║    ║
║   ██║╚██╗██║██║   ██║██╔══██║    ╚════██║██║▄▄ ██║    ║
║   ██║ ╚████║╚██████╔╝██║  ██║    ███████║╚██████╔╝    ║
║   ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝ ╚══▀▀═╝     ║
║                                                       ║
║           NOA SQL Scanner v1.9.0.3                    ║
║           Automated Web Security Testing              ║
║           Created by Nüvit Onur Altaş                 ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
{Colors.ENDC}
{Colors.WARNING}⚠️  WARNING: Use only on authorized targets!{Colors.ENDC}
{Colors.WARNING}⚠️  Unauthorized testing is illegal!{Colors.ENDC}
"""
