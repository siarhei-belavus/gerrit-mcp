"""MCP tools for Gerrit review and comment operations.
"""
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context

from gerrit import create_draft_comment, set_review
from utils.error_handling import log_and_format_error

# Set up logging
logger = logging.getLogger(__name__)


async def create_draft_comment_tool(
    change_id: str,
    file_path: str,
    message: str,
    line: int,
    ctx: Context,
) -> Dict[str, Any]:
    """Create a new draft comment on a specific line in a file for the current revision.
    If line is -1, creates a global comment on the file without line number.

    Args:
        change_id (str): The ID of the change to create a comment for
        file_path (str): The path of the file to comment on
        message (str): The content of the comment
        line (int): The line number to comment on (-1 for file-level comment)
        ctx (Context): The MCP context object

    Returns:
        Dict[str, Any]: A dictionary containing the created comment

    """
    try:
        logger.info(f"Creating draft comment for {file_path}:{line} in change: {change_id}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        # Input validation
        if not file_path:
            return {"error": "File path is required"}

        if not message:
            return {"error": "Comment message is required"}

        # Handle file-level comments (line = -1)
        line_param = None if line == -1 else line

        result = await create_draft_comment(
            change_id=change_id,
            file_path=file_path,
            message=message,
            line=line_param,
            session=session,
        )

        return result
    except Exception as e:
        return log_and_format_error(e, f"creating draft comment for {file_path}:{line} in {change_id}")


async def set_review_tool(
    change_id: str,
    code_review_label: int,
    ctx: Context,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit all draft comments for a change and apply the specified Code-Review label.

    Args:
        change_id (str): The ID of the change to review
        code_review_label (int): The value for the Code-Review label (-1 or -2)
        ctx (Context): The MCP context object
        message (Optional[str], optional): An optional message to include with the review. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the review submission

    """
    try:
        logger.info(f"Setting review for change {change_id} with label: {code_review_label}")
        session = ctx.request_context.lifespan_context.get("gerrit_session")
        if not session:
            return {"error": "Gerrit session not available"}

        # Input validation
        if code_review_label not in [-1, -2]:
            return {"error": f"Invalid Code-Review label value: {code_review_label}. Must be -1 or -2."}

        result = await set_review(
            change_id=change_id,
            code_review_label=code_review_label,
            message=message,
            session=session,
        )

        return result
    except Exception as e:
        return log_and_format_error(e, f"setting review for {change_id}")
