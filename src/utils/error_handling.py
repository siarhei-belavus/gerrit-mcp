"""Error handling utilities for MCP tools."""

import json
import logging
import traceback
from typing import Any, Dict, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)


def format_error_response(error: Union[str, Exception]) -> Dict[str, str]:
    """Format an error response as a dictionary.

    Args:
        error (Union[str, Exception]): The error to format

    Returns:
        Dict[str, str]: A dictionary with an 'error' key containing the formatted error message

    """
    error_msg = str(error)
    if isinstance(error, Exception):
        error_msg = f"{error.__class__.__name__}: {error_msg}"
    return {"error": error_msg}


def log_and_format_error(error: Exception, context: Optional[str] = None) -> Dict[str, str]:
    """Log an exception with traceback and return a formatted error response.

    Args:
        error (Exception): The exception to log and format
        context (Optional[str], optional): Additional context for the error. Defaults to None.

    Returns:
        Dict[str, str]: A dictionary with an 'error' key containing the formatted error message

    """
    context_str = f" during {context}" if context else ""
    logger.error(f"Error{context_str}: {error!s}")
    logger.error(traceback.format_exc())
    return format_error_response(error)


def is_error_response(response: Dict[str, Any]) -> bool:
    """Check if a response dictionary indicates an error.

    Args:
        response (Dict[str, Any]): The response to check

    Returns:
        bool: True if the response indicates an error, False otherwise

    """
    return isinstance(response, dict) and "error" in response


def safe_json_dumps(obj: Any, default_message: str = "Error serializing object") -> str:
    """Safely convert an object to a JSON string, handling exceptions.

    Args:
        obj (Any): The object to convert to JSON
        default_message (str, optional): Default message if serialization fails. Defaults to "Error serializing object".

    Returns:
        str: The JSON string, or an error message if serialization fails

    """
    try:
        return json.dumps(obj)
    except Exception as e:
        logger.error(f"Error serializing object to JSON: {e!s}")
        return json.dumps({"error": default_message})
