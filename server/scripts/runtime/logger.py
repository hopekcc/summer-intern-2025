import logging
import json
import os
import sys
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from queue import Queue
from contextvars import ContextVar
from datetime import datetime, timezone
import atexit

# Built-in defaults with environment variable overrides
def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "on", "y", "t"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
CONSOLE_LOG_LEVEL = os.getenv("CONSOLE_LOG_LEVEL", "WARNING").upper()
FILE_LOG_LEVEL = os.getenv("FILE_LOG_LEVEL", LOG_LEVEL).upper()
LOG_TO_CONSOLE = _env_bool("LOG_TO_CONSOLE", True)
LOG_TO_FILE = _env_bool("LOG_TO_FILE", True)
LOG_JSON = _env_bool("LOG_JSON", False)  # Human-readable logs by default
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(50 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_ASYNC_QUEUE = _env_bool("LOG_ASYNC_QUEUE", True)  # Keep async queue for app logger handlers
DB_LOG_LEVEL = os.getenv("DB_LOG_LEVEL", "WARNING").upper()  # DB/driver logs default to WARNING
UVICORN_ACCESS_LEVEL = os.getenv("UVICORN_ACCESS_LEVEL", "INFO").upper()  # Uvicorn access logs default to INFO

# Ensure logs/ directory exists (dev usage)
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

# Context for correlation IDs
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

class RequestIdFilter(logging.Filter):
    """Inject request_id from ContextVar into records if not already present."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if not hasattr(record, "request_id"):
                rid = request_id_ctx.get()
                if rid is not None:
                    setattr(record, "request_id", rid)
        except Exception:
            # Never block logging on filter errors
            pass
        return True

class JSONFormatter(logging.Formatter):
    def __init__(self, ensure_ascii: bool = False):
        super().__init__()
        self.ensure_ascii = ensure_ascii
    def _ts(self, record: logging.LogRecord) -> str:
        # Faster UTC timestamp with millisecond precision
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self._ts(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Structured extras if provided via logger(..., extra={...})
        extras = {
            "request_id",
            "uid",
            "room_id",
            "song_id",
            "page",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "ws_event",
            "chunk_index",
            "chunk_count",
            "recipient_count",
        }
        for key in extras:
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data, ensure_ascii=self.ensure_ascii, separators=(",", ":"))

class AsciiSafeFilter(logging.Filter):
    """Ensure record fields are ASCII-only to avoid console encoding issues."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = record.msg.encode("ascii", "replace").decode("ascii")
            # Sanitize common extra fields that may be strings
            for key in [
                "request_id", "uid", "room_id", "song_id", "page", "method", "path",
                "status_code", "client_ip", "ws_event"
            ]:
                if hasattr(record, key):
                    val = getattr(record, key)
                    if isinstance(val, str):
                        setattr(record, key, val.encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass
        return True

def _build_handlers():
    handlers = []
    # Console handler (stdout)
    if LOG_TO_CONSOLE:
        stream = logging.StreamHandler(stream=sys.stdout)
        stream.setLevel(getattr(logging, CONSOLE_LOG_LEVEL, logging.WARNING))
        if LOG_JSON:
            # Use ASCII-safe JSON for console to avoid UnicodeEncodeError on Windows
            stream.setFormatter(JSONFormatter(ensure_ascii=True))
        else:
            stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        # Sanitize any non-ASCII text for console output
        stream.addFilter(AsciiSafeFilter())
        handlers.append(stream)

    # Rotating file handlers (dev/local)
    if LOG_TO_FILE:
        info_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "info.log"), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        info_handler.setLevel(getattr(logging, FILE_LOG_LEVEL, logging.INFO))
        if LOG_JSON:
            info_handler.setFormatter(JSONFormatter(ensure_ascii=False))
        else:
            info_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        handlers.append(info_handler)

        error_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "error.log"), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        if LOG_JSON:
            error_handler.setFormatter(JSONFormatter(ensure_ascii=False))
        else:
            error_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        handlers.append(error_handler)
    return handlers

def _configure_db_loggers(app_logger: logging.Logger):
    """Route SQLAlchemy/asyncpg logs through our handlers and inject request_id."""
    db_logger_names = [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "asyncpg",
    ]
    for name in db_logger_names:
        lgr = logging.getLogger(name)
        # Set level and add our request_id filter
        try:
            lgr.setLevel(getattr(logging, DB_LOG_LEVEL, logging.WARNING))
        except Exception:
            lgr.setLevel(logging.WARNING)
        # Avoid adding duplicate filters
        has_filter = any(isinstance(f, RequestIdFilter) for f in getattr(lgr, 'filters', []))
        if not has_filter:
            lgr.addFilter(RequestIdFilter())

        # Attach to our async queue or handlers
        try:
            if LOG_ASYNC_QUEUE and hasattr(app_logger, "_listener") and hasattr(app_logger, "_queue"):
                # Ensure one QueueHandler using same queue
                q = getattr(app_logger, "_queue")
                already = any(isinstance(h, QueueHandler) and getattr(h, 'queue', None) is q for h in lgr.handlers)
                if not already:
                    lgr.addHandler(QueueHandler(q))
                lgr.propagate = False
            else:
                # Mirror app logger handlers directly
                app_handlers = list(getattr(app_logger, 'handlers', []))
                # Add only missing handlers (by class/type) to avoid duplicates
                existing_types = {type(h) for h in lgr.handlers}
                for h in app_handlers:
                    if type(h) not in existing_types:
                        lgr.addHandler(h)
                lgr.propagate = False
        except Exception:
            # If wiring fails, let them propagate to root
            pass

def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers (e.g., when reloaded)
    if not getattr(logger, "_configured", False):
        handlers = _build_handlers()
        # Add correlation filter to root app logger so child loggers inherit it
        logger.addFilter(RequestIdFilter())
        if LOG_ASYNC_QUEUE:
            queue = Queue(-1)
            qh = QueueHandler(queue)
            logger.addHandler(qh)
            listener = QueueListener(queue, *handlers, respect_handler_level=True)
            listener.start()
            logger._listener = listener  # type: ignore[attr-defined]
            logger._queue = queue        # type: ignore[attr-defined]
        else:
            for h in handlers:
                logger.addHandler(h)
        logger.propagate = False
        logger._configured = True  # type: ignore[attr-defined]
        # Wire DB/driver loggers to share our handlers and request_id context
        _configure_db_loggers(logger)

    return logger

# Export logger instance for convenience imports
logger = _configure_logger()

# Stop QueueListener cleanly at process exit (if enabled)
def _shutdown_logging_listener():
    try:
        if hasattr(logger, "_listener"):
            logger._listener.stop()  # type: ignore[attr-defined]
    except Exception:
        pass

atexit.register(_shutdown_logging_listener)

# Helper APIs to manage request_id context
def set_request_id(request_id: str | None):
    """Set the current request_id for log correlation (returns reset token)."""
    return request_id_ctx.set(request_id)

def reset_request_id(token):
    """Reset the request_id context using a token returned from set_request_id."""
    try:
        request_id_ctx.reset(token)
    except Exception:
        pass
