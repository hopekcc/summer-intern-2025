import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure logs/ directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Formatter with request details
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Info logger
info_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "info.log"), maxBytes=2*1024*1024, backupCount=3
)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Error logger
error_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "error.log"), maxBytes=2*1024*1024, backupCount=3
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Unified logger setup
logger = logging.getLogger("fastapi_logger")
logger.setLevel(logging.INFO)
logger.addHandler(info_handler)
logger.addHandler(error_handler)
