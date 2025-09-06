"""
Application Constants
Centralized definition of magic numbers, hardcoded values, and application constants.
Extracted from across the codebase for better maintainability and consistency.
"""

import os

# ============================================================================
# DATABASE CONSTANTS
# ============================================================================

# Default database pool sizes by environment
DB_POOL_SIZE_PRODUCTION = 8
DB_POOL_SIZE_DEVELOPMENT = 5

# Default database overflow limits by environment  
DB_MAX_OVERFLOW_PRODUCTION = 10
DB_MAX_OVERFLOW_DEVELOPMENT = 5

# Database connection timeouts (seconds)
DB_POOL_TIMEOUT_DEFAULT = 30
DB_POOL_RECYCLE_DEFAULT = 3600  # 1 hour
DB_HEALTHCHECK_TIMEOUT_DEFAULT = 2.0

# Statement cache sizes by environment
DB_STMT_CACHE_SIZE_PRODUCTION = 1000
DB_STMT_CACHE_SIZE_DEVELOPMENT = 500

# ============================================================================
# LOGGING CONSTANTS
# ============================================================================

# Log file rotation settings
LOG_MAX_BYTES_DEFAULT = 50 * 1024 * 1024  # 50 MB
LOG_BACKUP_COUNT_DEFAULT = 5

# Log directory relative path
LOG_DIR_RELATIVE = "logs"

# ============================================================================
# WEBSOCKET CONSTANTS
# ============================================================================

# WebSocket server settings
WEBSOCKET_PORT_DEFAULT = 8766

# WebSocket queue and performance limits
WS_SEND_QUEUE_MAX_DEFAULT = 100
WS_COALESCE_WINDOW_MS_DEFAULT = 50

# WebSocket message size limits (bytes)
WS_AUTO_FRAGMENT_SIZE_DEFAULT = 65536      # 64 KB
WS_MAX_MESSAGE_BYTES_DEFAULT = 1048576     # 1 MB  
WS_YIELD_THRESHOLD_BYTES_DEFAULT = 262144  # 256 KB

# WebSocket timeout settings (seconds)
WS_CONTENT_LOAD_TIMEOUT = 10

# ============================================================================
# ETAG AND CACHING CONSTANTS
# ============================================================================

# Valid ETag bit lengths for image caching
ETAG_VALID_BIT_LENGTHS = (64, 128, 256)
ETAG_DEFAULT_BITS = 128

# ============================================================================
# SEARCH INFRASTRUCTURE CONSTANTS
# ============================================================================

# Search setup defaults
SEARCH_CONCURRENT_INDEXES_DEFAULT = True
SEARCH_FTS_MODE_DEFAULT = "column"

# ============================================================================
# EXTERNAL TOOL CONSTANTS
# ============================================================================

# Song scraper defaults
SONGS_DIR_DEFAULT = "songs"
COMMIT_TO_GIT_DEFAULT = False

# ChordPro processing
CHORDPRO_RENDER_TIMEOUT = 60  # seconds

# ============================================================================
# HTTP AND API CONSTANTS
# ============================================================================

# HTTP status codes (commonly used)
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_INTERNAL_SERVER_ERROR = 500

# Request header names
REQUEST_ID_HEADER_DEFAULT = "X-Request-ID"

# ============================================================================
# FILE SYSTEM CONSTANTS
# ============================================================================

# Supported chord file extensions
CHORD_FILE_EXTENSIONS = (".pro", ".cho", ".chopro")

# Safe filename replacement patterns
UNSAFE_FILENAME_CHARS = (os.sep, "..")
SAFE_FILENAME_REPLACEMENT = "_"

# ============================================================================
# PERFORMANCE AND TIMING CONSTANTS
# ============================================================================

# Selenium wait timeouts (seconds)
SELENIUM_PAGE_LOAD_TIMEOUT = 2
SELENIUM_ELEMENT_WAIT_TIMEOUT = 10

# Database operation timeouts
DB_STARTUP_TIMEOUT = 60  # seconds

# Process execution timeouts
SUBPROCESS_DEFAULT_TIMEOUT = 60  # seconds

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

# Minimum Python version requirement
MIN_PYTHON_VERSION = (3, 8)

# Chord pattern validation
CHORD_PATTERN_REGEX = r'^[A-G][#b]?(?:m|maj|min|dim|aug|sus|add)?\d*(?:/[A-G][#b]?)?$'

# ChordPro validation patterns
CHORDPRO_CHORD_PATTERN = r"\[[A-G]"

# ============================================================================
# BOOLEAN PARSING VALUES
# ============================================================================

# Values that evaluate to True when parsing environment variables
TRUTHY_VALUES = {"1", "true", "yes", "on", "y", "t"}
FALSY_VALUES = {"0", "false", "no", "off", "n", "f"}

# ============================================================================
# ERROR MESSAGES
# ============================================================================

# Authentication error messages
AUTH_ERROR_MISSING_TOKEN = "Authentication required"
AUTH_ERROR_INVALID_TOKEN = "Invalid authentication token"
AUTH_ERROR_EXPIRED_TOKEN = "Authentication token has expired"
AUTH_ERROR_FORBIDDEN = "You don't have permission to perform this action"
AUTH_ERROR_ROOM_NOT_FOUND = "Room not found"
AUTH_ERROR_NOT_HOST = "Only the room host can perform this action"

# Database error messages
DB_ERROR_URL_MISSING = "DATABASE_URL must be set and use postgresql+asyncpg (PostgreSQL-only)."
DB_ERROR_UNSUPPORTED_DRIVER = "Unsupported DATABASE_URL. This project is PostgreSQL-only. Use postgresql+asyncpg://USER:PASS@HOST:PORT/DBNAME"

# Configuration error messages
CONFIG_ERROR_INVALID_ETAG_BITS = "ETAG_BITS must be 64, 128, or 256"
CONFIG_ERROR_POSITIVE_POOL_SIZE = "Database pool_size must be positive"
CONFIG_ERROR_NON_NEGATIVE_OVERFLOW = "Database max_overflow cannot be negative"
CONFIG_ERROR_POSITIVE_TIMEOUT = "Database pool_timeout must be positive"

# ============================================================================
# URL PATTERNS AND ENDPOINTS
# ============================================================================

# Ultimate Guitar search URL pattern
ULTIMATE_GUITAR_SEARCH_URL = "https://www.ultimate-guitar.com/search.php?search_type=title&value={query}"

# Chordie base URL
CHORDIE_BASE_URL = "https://www.chordie.com/"

# GitHub API URL pattern for song repository
GITHUB_API_URL_PATTERN = "https://api.github.com/repos/hopekcc/song-db-chordpro/contents/"

# ============================================================================
# REQUIRED PACKAGES
# ============================================================================

# Required Python packages for the application
REQUIRED_PACKAGES = [
    ("sqlalchemy", "SQLAlchemy"),
    ("asyncpg", "asyncpg"),
    ("httpx", "HTTPX"),
    ("PIL", "Pillow"),
    ("fitz", "PyMuPDF"),
    ("reportlab", "ReportLab"),
    ("dotenv", "python-dotenv")
]

# ============================================================================
# SECURITY CONSTANTS
# ============================================================================

# Password masking pattern for logs
PASSWORD_MASK = "***REDACTED***"
