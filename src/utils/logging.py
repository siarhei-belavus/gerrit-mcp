"""
Logging utilities for MCP tools.
"""
import logging
import os
import sys
from typing import Optional, Union, Dict, Any


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level (int, optional): Logging level. Defaults to logging.INFO.
        log_file (Optional[str], optional): Path to log file. Defaults to None (console only).
        log_format (str, optional): Log message format. Defaults to standard format with timestamp.
    """
    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if requested)
    if log_file:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: The logger
    """
    return logging.getLogger(name)


def log_request(logger: logging.Logger, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an API request.
    
    Args:
        logger (logging.Logger): The logger to use
        method (str): HTTP method
        url (str): Request URL
        data (Optional[Dict[str, Any]], optional): Request data. Defaults to None.
    """
    logger.info(f"Making {method} request to {url}")
    if data and logger.isEnabledFor(logging.DEBUG):
        # Only log data at debug level to avoid exposing sensitive information
        import json
        logger.debug(f"Request data: {json.dumps(data)}")


def log_response(
    logger: logging.Logger, 
    status: Union[int, str], 
    url: str, 
    response_text: str, 
    max_length: int = 200
) -> None:
    """
    Log an API response.
    
    Args:
        logger (logging.Logger): The logger to use
        status (Union[int, str]): HTTP status code or status string
        url (str): Request URL
        response_text (str): Response text
        max_length (int, optional): Maximum length of response text to log. Defaults to 200.
    """
    truncated = response_text[:max_length] + "..." if len(response_text) > max_length else response_text
    logger.debug(f"Response ({status}) for {url}: {truncated}")


def log_error(
    logger: logging.Logger, 
    error: Union[str, Exception], 
    context: Optional[str] = None
) -> None:
    """
    Log an error with context.
    
    Args:
        logger (logging.Logger): The logger to use
        error (Union[str, Exception]): The error to log
        context (Optional[str], optional): Additional context. Defaults to None.
    """
    context_str = f" during {context}" if context else ""
    if isinstance(error, Exception):
        logger.error(f"Error{context_str}: {error.__class__.__name__}: {str(error)}")
    else:
        logger.error(f"Error{context_str}: {error}") 