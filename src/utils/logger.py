import logging
import sys
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log messages by removing sensitive information.
    
    Args:
        message: The log message to sanitize
        
    Returns:
        Sanitized message with sensitive data redacted
    """
    # Redact API keys
    message = re.sub(
        r'(api[_-]?key[\'"]?\s*[:=]\s*[\'"]?)([^\'"]+)',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # Redact passwords
    message = re.sub(
        r'(password[\'"]?\s*[:=]\s*[\'"]?)([^\'"]+)',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # Redact OpenAI API keys (sk- prefix)
    message = re.sub(
        r'\bsk-[a-zA-Z0-9]{48}\b',
        'sk-***REDACTED***',
        message
    )
    
    # Redact tokens
    message = re.sub(
        r'(bearer\s+)[a-zA-Z0-9\-_.]{20,}',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    
    # Redact credit card numbers
    message = re.sub(
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        '****-****-****-****',
        message
    )
    
    # Redact email addresses (partially)
    message = re.sub(
        r'\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[A-Z|a-z]{2,})\b',
        r'***@\2',
        message
    )
    
    # Redact phone numbers
    message = re.sub(
        r'\b1[3-9]\d{9}\b',
        '***-****-****',
        message
    )
    
    return message


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that redacts sensitive information from log messages.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by sanitizing the message.
        
        Args:
            record: The log record to filter
            
        Returns:
            Always True (we don't block records, just sanitize them)
        """
        # Sanitize the main message
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)
        
        # Sanitize arguments
        if record.args:
            try:
                sanitized_args = tuple(
                    sanitize_log_message(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
                record.args = sanitized_args
            except (TypeError, ValueError):
                # If sanitization fails, keep original args
                pass
        
        return True


class ColoredFormatter(logging.Formatter):
    """
    Colored log formatter for console output.
    Only adds colors in terminal environments.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, fmt: str, datefmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a production-ready logger.
    
    Features:
    - Console output with colors (in DEBUG mode)
    - File output with rotation (in production mode)
    - Sensitive data filtering
    - Structured logging format
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Import settings here to avoid circular import
    from config import settings
    
    # Set log level
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)
    
    # ===== Console Handler =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Use colored formatter for console in debug mode
    if settings.DEBUG:
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            use_colors=True
        )
    else:
        console_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)
    
    # ===== File Handler (Production Mode Only) =====
    if not settings.DEBUG:
        try:
            # Get log directory
            log_dir = settings.get_log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / "luxselect.log"
            
            # Create rotating file handler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=settings.LOG_MAX_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
            # Detailed format for file logs
            file_formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            
            file_handler.setFormatter(file_formatter)
            file_handler.addFilter(SensitiveDataFilter())
            logger.addHandler(file_handler)
            
            logger.info(f"📝 Logging to file: {log_file}")
        
        except Exception as e:
            # If file logging fails, log to console only
            logger.warning(f"Failed to setup file logging: {e}")
    
    return logger

