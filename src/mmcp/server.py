"""
MCP server implementation for Gerrit code reviews.
"""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os
from typing import Dict, Any

import aiohttp
import asyncio
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base

from gerrit.auth import create_auth_session, validate_auth
from utils.logging import configure_logging
from mmcp.tools import (
    get_commit_info_tool,
    get_change_detail_tool,
    get_commit_message_tool,
    get_related_changes_tool,
    get_file_list_tool,
    get_file_diff_tool,
    create_draft_comment_tool,
    set_review_tool
)
from gerrit.api import (
    get_commit_info,
    get_change_detail,
    get_commit_message,
    get_related_changes,
    get_file_list,
    get_file_diff,
    create_draft_comment,
    set_review
)

import argparse

# Configure logging
configure_logging(level=logging.INFO)

# Get logger
logger = logging.getLogger(__name__)

# Default timeout for async operations (seconds)
AUTH_TIMEOUT = 30

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Run the Gerrit MCP server.')
parser.add_argument('--gerrit-url', type=str, help='The URL of the Gerrit server')
parser.add_argument('--username', type=str, help='The username for Gerrit authentication')
parser.add_argument('--api-token', type=str, help='The API token for Gerrit authentication')
args = parser.parse_args()

# Use command-line arguments if provided, otherwise fall back to environment variables
GERRIT_URL = args.gerrit_url or os.getenv('GERRIT_URL')
GERRIT_USERNAME = args.username or os.getenv('GERRIT_USERNAME')
GERRIT_API_TOKEN = args.api_token or os.getenv('GERRIT_API_TOKEN')

# Ensure all required values are set
if not all([GERRIT_URL, GERRIT_USERNAME, GERRIT_API_TOKEN]):
    raise ValueError('GERRIT_URL, GERRIT_USERNAME, and GERRIT_API_TOKEN must be provided either as arguments or environment variables.')

@asynccontextmanager
async def gerrit_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, aiohttp.ClientSession]]:
    """
    Manage the Gerrit aiohttp session lifecycle.
    
    Args:
        server (FastMCP): The FastMCP server instance
        
    Yields:
        Dict[str, aiohttp.ClientSession]: A dictionary containing the Gerrit session
    """
    logger.info("MCP Server starting up...")
    session: aiohttp.ClientSession = None
    
    try:
        # Log details about the server instance
        server_id = id(server)
        logger.info(f"Server instance ID: {server_id}")
        logger.info(f"Server name: {server.name}")
        logger.info(f"Server settings: {server.settings}")
        
        # Check if description attribute exists
        if hasattr(server, 'description'):
            logger.info(f"Server description: {server.description}")
        
        # Create an authenticated session
        logger.info(f"Creating authenticated Gerrit session... (server: {server_id})")
        try:
            session = create_auth_session(GERRIT_URL, GERRIT_USERNAME, GERRIT_API_TOKEN)
            logger.info(f"Session created successfully (server: {server_id})")
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise
        
        # Validate authentication with timeout
        logger.info(f"Validating Gerrit authentication... (server: {server_id})")
        try:
            auth_valid = await asyncio.wait_for(validate_auth(session, GERRIT_URL, GERRIT_USERNAME), timeout=AUTH_TIMEOUT)
            if not auth_valid:
                logger.error(f"Authentication validation failed (server: {server_id})")
                raise ValueError("Authentication validation failed")
            logger.info(f"Gerrit authentication validated successfully (server: {server_id})")
        except asyncio.TimeoutError:
            logger.error(f"Authentication validation timed out after {AUTH_TIMEOUT} seconds (server: {server_id})")
            if session and not session.closed:
                await session.close()
            raise ValueError("Authentication validation timed out")
        except Exception as e:
            logger.error(f"Error during authentication validation: {str(e)} (server: {server_id})")
            if session and not session.closed:
                await session.close()
            raise
        
        logger.info(f"Gerrit client session created successfully (server: {server_id})")
        
        # Set a flag on the session to identify it
        setattr(session, "_server_id", server_id)
        
        # Log the lifespan context before yielding it
        context = {"gerrit_session": session}
        logger.info(f"Yielding lifespan context: {context} (server: {server_id})")
        yield context
        logger.info(f"After yield in gerrit_lifespan (server: {server_id})")
    except Exception as e:
        logger.error(f"Error in gerrit_lifespan: {str(e)}")
        raise
    finally:
        server_id = getattr(server, "id", id(server))
        if session and not session.closed:
            logger.info(f"Closing Gerrit client session... (server: {server_id})")
            try:
                await asyncio.wait_for(session.close(), timeout=5)
                logger.info(f"Gerrit client session closed (server: {server_id})")
            except asyncio.TimeoutError:
                logger.warning(f"Closing Gerrit session timed out (server: {server_id})")
            except Exception as e:
                logger.error(f"Error closing session: {str(e)} (server: {server_id})")
        else:
            logger.info(f"No active Gerrit session to close or session already closed (server: {server_id})")
        logger.info(f"MCP Server shutting down (server: {server_id})")


# Create a FastMCP server with a descriptive name and lifespan manager
app = FastMCP(
    "Gerrit Review Server",
    description="A server that provides access to Gerrit code review functionality",
    lifespan=gerrit_lifespan,
    dependencies=["aiohttp", "python-dotenv"]
)


# === Define MCP Resources ===

@app.resource("gerrit://config")
def get_gerrit_config() -> Dict[str, Any]:
    """
    Return Gerrit configuration information.
    
    Returns:
        Dict[str, Any]: Configuration information including version and capabilities
    """
  
    return {
        "base_url":GERRIT_URL,
        "version": "1.0.0",
        "capabilities": ["code-review", "submit"]
    }


# === Define MCP Tools ===

@app.tool("gerrit_get_commit_info")
async def gerrit_get_commit_info_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Fetch commit information for the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get commit info for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing commit information.
    """
    ctx.info(f"Fetching commit info for change: {change_id}")
    return await get_commit_info(change_id, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_get_change_detail")
async def gerrit_get_change_detail_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get detailed information about a change.
    
    Args:
        change_id (str): The ID of the change to get details for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing change details.
    """
    ctx.info(f"Fetching change details for: {change_id}")
    return await get_change_detail(change_id, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_get_commit_message")
async def gerrit_get_commit_message_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get the commit message for the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get the commit message for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing the commit message.
    """
    ctx.info(f"Fetching commit message for: {change_id}")
    return await get_commit_message(change_id, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_get_related_changes")
async def gerrit_get_related_changes_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get related changes for the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get related changes for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing related changes.
    """
    ctx.info(f"Fetching related changes for: {change_id}")
    return await get_related_changes(change_id, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_get_file_list")
async def gerrit_get_file_list_tool(change_id: str, ctx: Context) -> Dict[str, Any]:
    """
    Get a detailed list of files for the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get the file list for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing the file list.
    """
    ctx.info(f"Fetching file list for: {change_id}")
    return await get_file_list(change_id, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_get_file_diff")
async def gerrit_get_file_diff_tool(change_id: str, file_path: str, ctx: Context) -> Dict[str, Any]:
    """
    Get the diff for a specific file in the current revision of a change.
    
    Args:
        change_id (str): The ID of the change to get the file diff for.
        file_path (str): The path of the file to get the diff for.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing the file diff.
    """
    ctx.info(f"Fetching file diff for: {change_id} {file_path}")
    return await get_file_diff(change_id, file_path, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"])


@app.tool("gerrit_create_draft_comment")
async def gerrit_create_draft_comment_tool(
    change_id: str, 
    file_path: str, 
    message: str, 
    line: int,
    ctx: Context
) -> Dict[str, Any]:
    """
    Create a draft comment on a change.
    
    Args:
        change_id (str): The ID of the change to create the comment on.
        file_path (str): The path of the file to comment on.
        message (str): The comment message.
        line (int): The line number to comment on, or -1 for a file-level comment.
        ctx (Context): The MCP context object.
        
    Returns:
        Dict[str, Any]: A dictionary containing the created comment.
    """
    line_desc = "file-level" if line == -1 else f"line {line}"
    ctx.info(f"Creating {line_desc} comment on {file_path} for change: {change_id}")
    
    try:
        result = await create_draft_comment(change_id, file_path, message, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"], line)
        return result
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        raise


@app.tool("gerrit_set_review")
async def gerrit_set_review_tool(
    change_id: str,
    code_review_label: int,
    ctx: Context,
    message: str = None
) -> Dict[str, Any]:
    """
    Set a review on a change.
    
    Args:
        change_id (str): The ID of the change to review.
        code_review_label (int): The Code-Review label value (-2, -1, 0, 1, 2).
        ctx (Context): The MCP context object.
        message (str, optional): Optional review message. If not provided, a default is used.
        
    Returns:
        Dict[str, Any]: A dictionary containing the review result.
    """
    ctx.info(f"Setting Code-Review={code_review_label} on change: {change_id}")
    
    if message is None:
        # Default messages based on Code-Review label
        if code_review_label == 2:
            message = "Looks good! Approved."
        elif code_review_label == 1:
            message = "Looks good with minor suggestions."
        elif code_review_label == 0:
            message = "No objections."
        elif code_review_label == -1:
            message = "Needs improvements before it can be approved."
        elif code_review_label == -2:
            message = "Cannot be merged as is."
    
    return await set_review(change_id, code_review_label, GERRIT_URL, ctx.request_context.lifespan_context["gerrit_session"], message)


# === Define MCP Prompts ===

@app.prompt()
def review_commit_prompt() -> list[base.Message]:
    """
    Prompt for reviewing a Gerrit commit.
    
    Returns:
        list[base.Message]: A list of prompt messages.
    """
    return [
        base.UserMessage("Please review the following Gerrit commit for issues, focusing on:"),
        base.UserMessage("1. Code quality and best practices"),
        base.UserMessage("2. Potential bugs or security issues"),
        base.UserMessage("3. Performance concerns"),
        base.UserMessage("4. Documentation and maintainability"),
        base.AssistantMessage("I'll review the commit. Let me first examine the commit details and changes.")
    ]


@app.prompt()
def comment_issues_prompt() -> list[base.Message]:
    """
    Prompt for commenting on issues in a Gerrit commit.
    
    Returns:
        list[base.Message]: A list of prompt messages.
    """
    return [
        base.UserMessage("Please review the code changes and create draft comments for any issues found."),
        base.UserMessage("For each issue:"),
        base.UserMessage("1. Identify the specific file and line number"),
        base.UserMessage("2. Describe the issue clearly"),
        base.UserMessage("3. Provide a suggestion for how to fix it"),
        base.UserMessage("4. Indicate if it's a critical issue (-2) or a non-critical issue (-1)"),
        base.AssistantMessage("I'll analyze the code changes and create draft comments for any issues I find.")
    ]


def main():
    app.run()

# Add run capability if executed directly
if __name__ == "__main__":
    main() 