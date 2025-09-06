"""
Centralized Configuration Management
Provides type-safe configuration with environment variable overrides and validation.
Separates sensitive credentials (kept in .env) from application settings.
"""

import os
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .constants import *


# ============================================================================
# CONFIGURATION ENUMS AND TYPES
# ============================================================================

class LogLevel(str, Enum):
    """Valid log levels for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FTSMode(str, Enum):
    """Full-text search modes for database setup."""
    NONE = "none"
    EXPR = "expr"
    COLUMN = "column"


class WSDropPolicy(str, Enum):
    """WebSocket message drop policies when queue is full."""
    OLDEST = "oldest"
    NEWEST = "newest"
    RANDOM = "random"


# ============================================================================
# CONFIGURATION UTILITIES
# ============================================================================

def _env_bool(name: str, default: bool) -> bool:
    """Parse boolean from environment variable with sensible defaults."""
    val = os.getenv(name)
    if val is None:
        return default
    s = str(val).strip().lower()
    return s in TRUTHY_VALUES


def _env_int(name: str, default: int) -> int:
    """Parse integer from environment variable with validation."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Parse float from environment variable with validation."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Get string from environment variable with default."""
    return os.getenv(name, default).strip()


def _env_enum(name: str, enum_class, default):
    """Parse enum from environment variable with validation."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return enum_class(val.upper())
    except ValueError:
        return default


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

@dataclass
class DatabaseConfig:
    """Database connection and performance settings."""
    
    # Production mode detection
    is_production: bool = field(default_factory=lambda: _env_bool("PROD", False))
    
    # Connection pool settings (defaults from constants)
    pool_size: int = field(default_factory=lambda: _env_int(
        "DB_POOL_SIZE", 
        DB_POOL_SIZE_PRODUCTION if _env_bool("PROD", False) else DB_POOL_SIZE_DEVELOPMENT
    ))
    
    max_overflow: int = field(default_factory=lambda: _env_int(
        "DB_MAX_OVERFLOW", 
        DB_MAX_OVERFLOW_PRODUCTION if _env_bool("PROD", False) else DB_MAX_OVERFLOW_DEVELOPMENT
    ))
    
    pool_timeout: int = field(default_factory=lambda: _env_int("DB_POOL_TIMEOUT", DB_POOL_TIMEOUT_DEFAULT))
    pool_recycle: int = field(default_factory=lambda: _env_int("DB_POOL_RECYCLE", DB_POOL_RECYCLE_DEFAULT))
    pool_pre_ping: bool = field(default_factory=lambda: _env_bool("DB_PRE_PING", True))
    pool_use_lifo: bool = field(default_factory=lambda: _env_bool("DB_POOL_USE_LIFO", True))
    
    # Statement cache settings (defaults from constants)
    stmt_cache_size: int = field(default_factory=lambda: _env_int(
        "DB_STMT_CACHE_SIZE", 
        DB_STMT_CACHE_SIZE_PRODUCTION if _env_bool("PROD", False) else DB_STMT_CACHE_SIZE_DEVELOPMENT
    ))
    
    # Debugging and logging
    echo_queries: bool = field(default_factory=lambda: _env_bool("DB_ECHO", False))
    log_level: LogLevel = field(default_factory=lambda: _env_enum("DB_LOG_LEVEL", LogLevel, LogLevel.WARNING))
    
    # Health check settings (defaults from constants)
    startup_check: bool = field(default_factory=lambda: _env_bool("DB_STARTUP_CHECK", False))
    healthcheck_timeout: float = field(default_factory=lambda: _env_float("DB_HEALTHCHECK_TIMEOUT", DB_HEALTHCHECK_TIMEOUT_DEFAULT))
    fail_on_startup_error: bool = field(default_factory=lambda: _env_bool("FAIL_ON_DB_STARTUP_ERROR", False))


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

@dataclass
class LoggingConfig:
    """Centralized logging configuration with environment overrides."""
    
    # Core log levels
    log_level: LogLevel = field(default_factory=lambda: _env_enum("LOG_LEVEL", LogLevel, LogLevel.INFO))
    console_log_level: LogLevel = field(default_factory=lambda: _env_enum("CONSOLE_LOG_LEVEL", LogLevel, LogLevel.WARNING))
    file_log_level: LogLevel = field(default_factory=lambda: _env_enum(
        "FILE_LOG_LEVEL", LogLevel, _env_enum("LOG_LEVEL", LogLevel, LogLevel.INFO)
    ))
    
    # Output destinations
    log_to_console: bool = field(default_factory=lambda: _env_bool("LOG_TO_CONSOLE", True))
    log_to_file: bool = field(default_factory=lambda: _env_bool("LOG_TO_FILE", True))
    log_json: bool = field(default_factory=lambda: _env_bool("LOG_JSON", False))
    
    # File rotation settings (defaults from constants)
    max_bytes: int = field(default_factory=lambda: _env_int("LOG_MAX_BYTES", LOG_MAX_BYTES_DEFAULT))
    backup_count: int = field(default_factory=lambda: _env_int("LOG_BACKUP_COUNT", LOG_BACKUP_COUNT_DEFAULT))
    
    # Performance settings
    async_queue: bool = field(default_factory=lambda: _env_bool("LOG_ASYNC_QUEUE", True))
    
    # Component-specific levels
    uvicorn_access_level: LogLevel = field(default_factory=lambda: _env_enum("UVICORN_ACCESS_LEVEL", LogLevel, LogLevel.INFO))


# ============================================================================
# WEBSOCKET CONFIGURATION
# ============================================================================

@dataclass
class WebSocketConfig:
    """WebSocket server performance and behavior settings."""
    
    # Server settings (defaults from constants)
    port: int = field(default_factory=lambda: _env_int("WEBSOCKET_PORT", WEBSOCKET_PORT_DEFAULT))
    
    # Request tracking (defaults from constants)
    request_id_header: str = field(default_factory=lambda: _env_str("REQUEST_ID_HEADER", REQUEST_ID_HEADER_DEFAULT))
    
    # Queue management (defaults from constants)
    send_queue_max: int = field(default_factory=lambda: _env_int("WS_SEND_QUEUE_MAX", WS_SEND_QUEUE_MAX_DEFAULT))
    coalesce_window_ms: int = field(default_factory=lambda: _env_int("WS_COALESCE_WINDOW_MS", WS_COALESCE_WINDOW_MS_DEFAULT))
    drop_policy: WSDropPolicy = field(default_factory=lambda: _env_enum("WS_DROP_POLICY", WSDropPolicy, WSDropPolicy.OLDEST))
    
    # Message size limits (defaults from constants)
    auto_fragment_size: int = field(default_factory=lambda: _env_int("WS_AUTO_FRAGMENT_SIZE", WS_AUTO_FRAGMENT_SIZE_DEFAULT))
    max_message_bytes: int = field(default_factory=lambda: _env_int("WS_MAX_MESSAGE_BYTES", WS_MAX_MESSAGE_BYTES_DEFAULT))
    yield_threshold_bytes: int = field(default_factory=lambda: _env_int("WS_YIELD_THRESHOLD_BYTES", WS_YIELD_THRESHOLD_BYTES_DEFAULT))


# ============================================================================
# APPLICATION FEATURE CONFIGURATION
# ============================================================================

@dataclass
class ApplicationConfig:
    """General application feature settings."""
    
    # ETag configuration for image caching (defaults from constants)
    etag_bits: int = field(default_factory=lambda: _env_int("ETAG_BITS", ETAG_DEFAULT_BITS))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.etag_bits not in ETAG_VALID_BIT_LENGTHS:
            raise ValueError(f"ETAG_BITS must be {ETAG_VALID_BIT_LENGTHS}, got {self.etag_bits}")


# ============================================================================
# SEARCH INFRASTRUCTURE CONFIGURATION
# ============================================================================

@dataclass
class SearchConfig:
    """Search infrastructure setup and behavior settings."""
    
    # Search feature toggles (defaults from constants)
    enable_search_indexes: bool = field(default_factory=lambda: _env_bool("ENABLE_SEARCH_INDEXES", True))
    concurrent_indexes: bool = field(default_factory=lambda: _env_bool("CONCURRENT_INDEXES", SEARCH_CONCURRENT_INDEXES_DEFAULT))
    
    # Full-text search configuration (defaults from constants)
    fts_mode: FTSMode = field(default_factory=lambda: _env_enum("FTS_MODE", FTSMode, FTSMode.COLUMN))


# ============================================================================
# EXTERNAL TOOL CONFIGURATION
# ============================================================================

@dataclass
class ExternalToolsConfig:
    """Configuration for external tools and integrations."""
    
    # ChordPro executable path (optional)
    chordpro_path: Optional[str] = field(default_factory=lambda: os.getenv("CHORDPRO_PATH"))
    
    # Song scraper settings (defaults from constants)
    songs_dir: str = field(default_factory=lambda: _env_str("SONGS_DIR", SONGS_DIR_DEFAULT))
    commit_to_git: bool = field(default_factory=lambda: _env_bool("COMMIT_TO_GIT", COMMIT_TO_GIT_DEFAULT))


# ============================================================================
# MASTER CONFIGURATION CLASS
# ============================================================================

@dataclass
class Config:
    """Master configuration class combining all settings."""
    
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    external_tools: ExternalToolsConfig = field(default_factory=ExternalToolsConfig)
    
    def validate(self) -> None:
        """Validate the entire configuration for consistency and correctness."""
        # Database validation
        if self.database.pool_size <= 0:
            raise ValueError(CONFIG_ERROR_POSITIVE_POOL_SIZE)
        if self.database.max_overflow < 0:
            raise ValueError(CONFIG_ERROR_NON_NEGATIVE_OVERFLOW)
        if self.database.pool_timeout <= 0:
            raise ValueError(CONFIG_ERROR_POSITIVE_TIMEOUT)
        if self.database.healthcheck_timeout <= 0:
            raise ValueError("Database healthcheck_timeout must be positive")
        
        # Logging validation
        if self.logging.max_bytes <= 0:
            raise ValueError("Log max_bytes must be positive")
        if self.logging.backup_count < 0:
            raise ValueError("Log backup_count cannot be negative")
        
        # WebSocket validation
        if self.websocket.port <= 0 or self.websocket.port > 65535:
            raise ValueError("WebSocket port must be between 1 and 65535")
        if self.websocket.send_queue_max <= 0:
            raise ValueError("WebSocket send_queue_max must be positive")
        if self.websocket.coalesce_window_ms < 0:
            raise ValueError("WebSocket coalesce_window_ms cannot be negative")
        if self.websocket.auto_fragment_size <= 0:
            raise ValueError("WebSocket auto_fragment_size must be positive")
        if self.websocket.max_message_bytes <= 0:
            raise ValueError("WebSocket max_message_bytes must be positive")
        
        # Cross-component validation
        if self.websocket.auto_fragment_size > self.websocket.max_message_bytes:
            raise ValueError("WebSocket auto_fragment_size cannot exceed max_message_bytes")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'database': {
                'is_production': self.database.is_production,
                'pool_size': self.database.pool_size,
                'max_overflow': self.database.max_overflow,
                'pool_timeout': self.database.pool_timeout,
                'pool_recycle': self.database.pool_recycle,
                'pool_pre_ping': self.database.pool_pre_ping,
                'pool_use_lifo': self.database.pool_use_lifo,
                'stmt_cache_size': self.database.stmt_cache_size,
                'echo_queries': self.database.echo_queries,
                'log_level': self.database.log_level.value,
                'startup_check': self.database.startup_check,
                'healthcheck_timeout': self.database.healthcheck_timeout,
                'fail_on_startup_error': self.database.fail_on_startup_error,
            },
            'logging': {
                'log_level': self.logging.log_level.value,
                'console_log_level': self.logging.console_log_level.value,
                'file_log_level': self.logging.file_log_level.value,
                'log_to_console': self.logging.log_to_console,
                'log_to_file': self.logging.log_to_file,
                'log_json': self.logging.log_json,
                'max_bytes': self.logging.max_bytes,
                'backup_count': self.logging.backup_count,
                'async_queue': self.logging.async_queue,
                'uvicorn_access_level': self.logging.uvicorn_access_level.value,
            },
            'websocket': {
                'port': self.websocket.port,
                'request_id_header': self.websocket.request_id_header,
                'send_queue_max': self.websocket.send_queue_max,
                'coalesce_window_ms': self.websocket.coalesce_window_ms,
                'drop_policy': self.websocket.drop_policy.value,
                'auto_fragment_size': self.websocket.auto_fragment_size,
                'max_message_bytes': self.websocket.max_message_bytes,
                'yield_threshold_bytes': self.websocket.yield_threshold_bytes,
            },
            'application': {
                'etag_bits': self.application.etag_bits,
            },
            'search': {
                'enable_search_indexes': self.search.enable_search_indexes,
                'concurrent_indexes': self.search.concurrent_indexes,
                'fts_mode': self.search.fts_mode.value,
            },
            'external_tools': {
                'chordpro_path': self.external_tools.chordpro_path,
                'songs_dir': self.external_tools.songs_dir,
                'commit_to_git': self.external_tools.commit_to_git,
            }
        }


# ============================================================================
# GLOBAL CONFIGURATION INSTANCE
# ============================================================================

# Create and validate the global configuration instance
config = Config()

try:
    config.validate()
except Exception as e:
    # Log the error but don't crash the application
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Configuration validation failed: {e}")
    raise


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def reload_config() -> Config:
    """Reload configuration from environment variables."""
    global config
    config = Config()
    config.validate()
    return config


def print_config_summary() -> None:
    """Print a summary of the current configuration for debugging."""
    print("=== CONFIGURATION SUMMARY ===")
    print(f"Production Mode: {config.database.is_production}")
    print(f"Database Pool Size: {config.database.pool_size}")
    print(f"Log Level: {config.logging.log_level.value}")
    print(f"Console Log Level: {config.logging.console_log_level.value}")
    print(f"WebSocket Queue Max: {config.websocket.send_queue_max}")
    print(f"ETag Bits: {config.application.etag_bits}")
    print(f"Search Enabled: {config.search.enable_search_indexes}")
    print(f"FTS Mode: {config.search.fts_mode.value}")
    print("=============================")


# Export commonly used configurations for convenience
db_config = config.database
log_config = config.logging
ws_config = config.websocket
app_config = config.application
search_config = config.search
tools_config = config.external_tools
