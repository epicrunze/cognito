"""
Logging configuration for Cognito backend.

Provides structured logging with JSON format for production
and human-readable format for development.
"""

import logging
import sys
from typing import Any


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configure and return the application logger.
    
    Args:
        debug: If True, use DEBUG level and verbose format.
               If False, use INFO level with JSON-like format.
    
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("cognito")
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set level based on debug mode
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Format based on environment
    if debug:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # Structured format for production
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Create default logger instance
logger = setup_logging(debug=True)


def get_logger(name: str = "cognito") -> logging.Logger:
    """
    Get a child logger with the specified name.
    
    Args:
        name: Logger name, will be prefixed with 'cognito.'
    
    Returns:
        Logger instance.
    """
    if name == "cognito":
        return logger
    return logger.getChild(name)


def log_with_context(
    level: int,
    message: str,
    **context: Any
) -> None:
    """
    Log a message with additional context fields.
    
    Args:
        level: Logging level (e.g., logging.INFO)
        message: Log message
        **context: Additional context fields
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        full_message = f"{message} | {context_str}"
    else:
        full_message = message
    
    logger.log(level, full_message)


def debug(message: str, **context: Any) -> None:
    """Log a debug message with optional context."""
    log_with_context(logging.DEBUG, message, **context)


def info(message: str, **context: Any) -> None:
    """Log an info message with optional context."""
    log_with_context(logging.INFO, message, **context)


def warning(message: str, **context: Any) -> None:
    """Log a warning message with optional context."""
    log_with_context(logging.WARNING, message, **context)


def error(message: str, **context: Any) -> None:
    """Log an error message with optional context."""
    log_with_context(logging.ERROR, message, **context)
