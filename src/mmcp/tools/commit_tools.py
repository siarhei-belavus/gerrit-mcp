"""MCP tools for Gerrit commit and change operations.
"""
import logging
from typing import Any, Dict

from mcp.server.fastmcp import Context

from gerrit import get_change_detail, get_commit_info, get_commit_message, get_related_changes
from utils.error_handling import log_and_format_error

# Set up logging
logger = logging.getLogger(__name__)


async def get_commit_info_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Fetch commit information for the current revision of a change.

    Args:
        change_id (str): The ID of the change to get commit info for
        ctx (Context): The MCP context object

    Returns:
        Dict[str, Any]: A dictionary containing commit information

    """
    try:
        logger.info(f"Getting commit info for change: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        result = await get_commit_info(change_id, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting commit info for {change_id}")


async def get_change_detail_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get detailed information about a change.

    Args:
        change_id (str): The ID of the change to get details for
        ctx (Context): The MCP context object

    Returns:
        Dict[str, Any]: A dictionary containing change details

    """
    try:
        logger.info(f"Getting change details for: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        result = await get_change_detail(change_id, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting change details for {change_id}")


async def get_commit_message_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get the commit message for the current revision of a change.

    Args:
        change_id (str): The ID of the change to get the commit message for
        ctx (Context): The MCP context object

    Returns:
        Dict[str, Any]: A dictionary containing the commit message

    """
    try:
        logger.info(f"Getting commit message for change: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        result = await get_commit_message(change_id, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting commit message for {change_id}")


async def get_related_changes_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get related changes for the current revision of a change.

    Args:
        change_id (str): The ID of the change to get related changes for
        ctx (Context): The MCP context object

    Returns:
        Dict[str, Any]: A dictionary containing related changes

    """
    try:
        logger.info(f"Getting related changes for: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        result = await get_related_changes(change_id, session)
        return result
    except Exception as e:
        return log_and_format_error(e, f"getting related changes for {change_id}")
