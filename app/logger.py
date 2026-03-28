import logging
import sys
from app.config import settings

# Formatter definitions
class CustomFormatter(logging.Formatter):
    """Custom logging formatter for production-level output."""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    cyan = "\x1b[36;20m"
    
    format_str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: cyan + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def setup_logger(name: str):
    """Create a logger instance for specific modules."""
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)

    # Console Handler
    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(settings.LOG_LEVEL)
        ch.setFormatter(CustomFormatter())
        logger.addHandler(ch)

    return logger

# Global loggers
main_logger = setup_logger("nexus.main")
auth_logger = setup_logger("nexus.auth")
db_logger = setup_logger("nexus.db")
match_logger = setup_logger("nexus.match")
ws_logger = setup_logger("nexus.websocket")
