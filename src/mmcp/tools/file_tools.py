"""
MCP tools for Gerrit file-related operations.
"""
import logging
from typing import Dict, Any

from mcp.server.fastmcp import Context

from gerrit import (
    get_file_list,
    get_file_diff
)
from utils.error_handling import log_and_format_error

# Set up logging
logger = logging.getLogger(__name__)


async def get_file_list_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get a detailed list of files for the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get the file list for
        ctx (Context): The MCP context object
        
    Returns:
        Dict[str, Any]: A dictionary containing the file list
    """
    try:
        logger.info(f"Getting file list for change: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}
        
        result = await get_file_list(change_id, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting file list for {change_id}")


async def get_file_diff_tool(change_id: str, file_path: str, ctx: Context) -> Dict[str, Any]:
    """
    Get the diff for a specific file in the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get the file diff for
        file_path (str): The path of the file to get the diff for
        ctx (Context): The MCP context object
        
    Returns:
        Dict[str, Any]: A dictionary containing the file diff
    """
    try:
        logger.info(f"Getting file diff for {file_path} in change: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}
        
        # Input validation
        if not file_path:
            return {"error": "File path is required"}
        
        result = await get_file_diff(change_id, file_path, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting file diff for {file_path} in {change_id}") 