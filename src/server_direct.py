#!/usr/bin/env python3
import os
import re
import json
import argparse
from typing import Dict, List, Optional, Any, Union
import aiohttp
from urllib.parse import urlparse, parse_qs, quote
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
from mcp import types

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Lifespan Management ---

@asynccontextmanager
async def gerrit_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, aiohttp.ClientSession]]:
    """Manage the Gerrit aiohttp session lifecycle."""
    logger.info("MCP Server starting up...")
    session: Optional[aiohttp.ClientSession] = None
    
    gerrit_url = os.environ.get("GERRIT_URL")
    username = os.environ.get("GERRIT_USERNAME")
    api_token = os.environ.get("GERRIT_API_TOKEN")

    if not all([gerrit_url, username, api_token]):
        missing = []
        if not gerrit_url: missing.append("GERRIT_URL")
        if not username: missing.append("GERRIT_USERNAME")
        if not api_token: missing.append("GERRIT_API_TOKEN")
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        # We raise here to prevent the server from starting without configuration.
        # Alternatively, could yield an empty dict and let tools fail, but failing fast is better.
        raise ValueError(error_msg)
    
    logger.info(f"Initializing Gerrit client for URL: {gerrit_url} with user: {username}")
    try:
        auth = aiohttp.BasicAuth(username, api_token)
        session = aiohttp.ClientSession(
            auth=auth, 
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        logger.info("Gerrit client session created successfully.")
        yield {"gerrit_session": session}
    finally:
        if session and not session.closed:
            logger.info("Closing Gerrit client session...")
            await session.close()
            logger.info("Gerrit client session closed.")
        else:
            logger.info("No active Gerrit session to close or session already closed.")
        logger.info("MCP Server shutting down.")

# --- End Lifespan Management ---

# Create a FastMCP server with a descriptive name and lifespan manager
app = FastMCP(
    "Gerrit Review Server",
    description="A server that provides access to Gerrit code review functionality",
    lifespan=gerrit_lifespan
)

# Custom Exceptions
class GerritAPIError(Exception):
    """Custom exception for Gerrit API errors."""
    pass

class ResourceNotFoundError(GerritAPIError):
    """Custom exception for when a Gerrit resource is not found."""
    pass

def parse_gerrit_response(response_text: str) -> Dict[str, Any]:
    """Parse the Gerrit API response, handling the magic prefix."""
    try:
        # Remove Gerrit's magic prefix if present
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]
        
        # Parse JSON response
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gerrit response: {str(e)}")
        logger.error(f"Response text: {response_text}")
        raise GerritAPIError(f"Invalid JSON response: {str(e)}")

async def make_gerrit_request(url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
    """Make a request to the Gerrit API with proper error handling."""
    # Session is now expected to be passed in from the tool handler via lifespan context
    if not session:
        # This should ideally not happen if lifespan is working correctly
        # Raise an error or handle appropriately
        error_msg = "Gerrit session not available. Lifespan context might be missing."
        logger.error(error_msg)
        raise GerritAPIError(error_msg) 
    
    gerrit_url = os.environ.get("GERRIT_URL") # Needed for URL reconstruction
    if not gerrit_url:
         # Should have been caught by lifespan, but double-check
         raise ValueError("GERRIT_URL environment variable not set")

    try:
        # Handle change IDs in URLs
        processed_url = url # Start with the original URL
        if '/changes/' in url:
            logger.info(f"Original URL: {url}")
            
            # Extract the change ID part relative to the base Gerrit URL
            # Ensure we correctly split based on the known gerrit_url
            if url.startswith(gerrit_url):
                relative_path = url[len(gerrit_url):].lstrip('/') # e.g., a/changes/project~123/detail
                path_parts_from_base = relative_path.split('/')
                
                # Find the 'changes' part
                try:
                    changes_index = path_parts_from_base.index('changes')
                    if changes_index + 1 < len(path_parts_from_base):
                        change_id_part = path_parts_from_base[changes_index + 1]
                        remaining_path_parts = path_parts_from_base[changes_index + 2:]
                        remaining_path = '/'.join(remaining_path_parts) if remaining_path_parts else ''
                        
                        logger.info(f"Extracted Change ID part: {change_id_part}")
                        logger.info(f"Extracted Remaining path: {remaining_path}")

                        # Keep the original change ID for error reporting
                        original_change_id = change_id_part
                        
                        # Encode the Change ID part correctly
                        encoded_change_id_part = change_id_part # Default to original if no encoding needed
                        if '~' in change_id_part:
                            parts = change_id_part.split('~')
                            if len(parts) == 2:
                                project, number = parts
                                encoded_change_id_part = f"{quote(project, safe='')}~{number}"
                                logger.info(f"Using encoded project~number format: {encoded_change_id_part}")
                            else:
                                encoded_change_id_part = '~'.join(quote(p, safe='') for p in parts)
                                logger.info(f"Using encoded full triple format: {encoded_change_id_part}")
                        elif not change_id_part.isdigit():
                             # Non-numeric, non-tilde assumed to be full ID needing encoding
                             encoded_change_id_part = quote(change_id_part, safe='')
                             logger.info(f"Using encoded change ID: {encoded_change_id_part}")
                        else:
                            logger.info(f"Using numeric change ID (no encoding needed): {change_id_part}")

                        # Reconstruct the URL - ensure /a/ prefix if needed
                        # The incoming URL might already have /a/
                        prefix = "/a/" if "/a/changes/" in url else "/"
                        processed_url = f"{gerrit_url}{prefix}changes/{encoded_change_id_part}"
                        if remaining_path:
                            processed_url = f"{processed_url}/{remaining_path}"
                        logger.info(f"Reconstructed URL: {processed_url}")
                    else:
                        logger.warning(f"Could not extract change ID part from URL: {url}")
                        processed_url = url # Fallback to original if parsing fails
                except ValueError:
                     logger.warning(f"'changes' segment not found in URL path: {url}")
                     processed_url = url # Fallback
            else:
                logger.warning(f"URL {url} does not start with expected GERRIT_URL {gerrit_url}")
                processed_url = url # Fallback
        else:
             # If URL doesn't contain /changes/, assume it's correct or handle other cases
             # Ensure /a/ prefix for authenticated endpoints if it's not a /changes/ URL
             # Example: /a/accounts/self/detail - needs /a/ but not /changes/
             if gerrit_url and url.startswith(gerrit_url) and '/a/' not in url:
                 relative_path = url[len(gerrit_url):].lstrip('/')
                 if not relative_path.startswith('a/'): # Avoid adding /a/ if already there somehow
                    processed_url = f"{gerrit_url}/a/{relative_path}"
                    logger.info(f"Added /a/ prefix for non-changes URL: {processed_url}")

        # Final check for /a/ prefix if it involves /changes/
        # This handles cases where the original URL might have been slightly malformed
        if '/changes/' in processed_url and '/a/changes/' not in processed_url:
             processed_url = processed_url.replace('/changes/', '/a/changes/')
             logger.info(f"Ensured /a/ prefix for changes URL: {processed_url}")

        logger.info(f"Making {method} request to {processed_url}")
        if data:
             logger.debug(f"Request Data: {json.dumps(data)}") # Log POST/PUT data

        async with session.request(method, processed_url, json=data) as response:
            response_text = await response.text()
            if response.status == 404:
                logger.warning(f"Resource not found (404): {processed_url}")
                raise ResourceNotFoundError(f"Resource not found: {processed_url}")
            elif response.status >= 400:
                logger.error(f"Gerrit API error ({response.status}) for {processed_url}: {response_text}")
                raise GerritAPIError(f"Gerrit API error ({response.status}): {response_text}")
            
            # Log successful responses too for debugging
            logger.debug(f"Gerrit response ({response.status}) for {processed_url}: {response_text[:200]}...") 
            return parse_gerrit_response(response_text)
            
    except aiohttp.ClientError as e:
        logger.error(f"Network error connecting to {processed_url}: {str(e)}")
        raise GerritAPIError(f"Network error: {str(e)}")
    except json.JSONDecodeError as e: # Should be caught by parse_gerrit_response, but as fallback
        logger.error(f"Invalid JSON response from {processed_url}: {str(e)}")
        raise GerritAPIError(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        if isinstance(e, (ResourceNotFoundError, GerritAPIError)):
            raise # Re-raise specific known errors
        logger.error(f"Unexpected error during Gerrit request to {processed_url}: {str(e)}")
        logger.exception("Traceback for unexpected error:") # Log full traceback
        raise GerritAPIError(f"Unexpected error: {str(e)}")

def format_error_response(error: Union[str, Exception]) -> str:
    """Format an error response as JSON."""
    error_msg = str(error)
    if isinstance(error, Exception):
        error_msg = f"{error.__class__.__name__}: {error_msg}"
    return json.dumps({"error": error_msg})

def extract_change_id(commit_url: str) -> Optional[str]:
    """Extract the change ID from a Gerrit commit URL."""
    try:
        # Parse the URL
        parsed = urlparse(commit_url)
        path = parsed.path
        
        # Extract the change ID from the path
        match = re.search(r'/\+/(\d+)(?:/\d+)?$', path)
        if match:
            return match.group(1)
        
        # Try to get it from query parameters
        query_params = parse_qs(parsed.query)
        if 'id' in query_params:
            return query_params['id'][0]
        
        return None
    except Exception as e:
        print(f"Error extracting change ID: {e}")
        return None

def chunk_changes(changes: List[Dict[str, Any]], max_files_per_chunk: int = 3) -> List[List[Dict[str, Any]]]:
    """Split changes into smaller chunks for review."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for change in changes:
        current_chunk.append(change)
        current_size += 1
        
        if current_size >= max_files_per_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0
    
    if current_chunk:  # Add any remaining changes
        chunks.append(current_chunk)
    
    return chunks

def format_changes_for_review(changes: List[Dict[str, Any]]) -> str:
    """Format a subset of changes for review."""
    formatted = []
    for change in changes:
        formatted.append(f"File: {change['file_path']}")
        formatted.append("Changes:")
        if isinstance(change['diff'], list):
            formatted.append("\n".join(str(line) for line in change['diff']))
        else:
            formatted.append(str(change['diff']))
        formatted.append("---")
    return "\n".join(formatted)

def generate_review_prompt(diff_content: str, guidelines: Optional[str] = None) -> List[types.PromptMessage]:
    """Generate a prompt for reviewing code changes."""
    messages = []
    
    # Add initial message with guidelines if available
    if guidelines:
        messages.append(types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text=f"""You are a code reviewer. Please review the code changes according to these guidelines:

{guidelines}

For each file, format your comments like this:
File: path/to/file
- Line X: Your comment about line X
- Line Y: Your comment about line Y
- General comment about the file

Focus on the most important issues first. If a file has no significant issues, you can skip it."""
            )
        ))
        messages.append(types.PromptMessage(
            role="assistant",
            content=types.TextContent(
                type="text",
                text="I understand. I will review the code changes according to the provided guidelines and format my comments as requested."
            )
        ))
    else:
        messages.append(types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text="""You are a code reviewer. Please review the code changes and provide constructive feedback.

For each file, format your comments like this:
File: path/to/file
- Line X: Your comment about line X
- Line Y: Your comment about line Y
- General comment about the file

Focus on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Documentation and readability

Focus on the most important issues first. If a file has no significant issues, you can skip it."""
            )
        ))
        messages.append(types.PromptMessage(
            role="assistant",
            content=types.TextContent(
                type="text",
                text="I understand. I will review the code changes and provide constructive feedback in the requested format."
            )
        ))
    
    # Add user message with the diff content
    messages.append(types.PromptMessage(
        role="user",
        content=types.TextContent(
            type="text",
            text=f"Please review these code changes:\n\n{diff_content}"
        )
    ))
    
    return messages

def extract_review_comments(messages: List[types.PromptMessage]) -> List[Dict[str, Any]]:
    """Extract review comments from the AI's response."""
    if not messages:
        return []
    
    # Get the last message (assistant's response)
    last_message = messages[-1]
    if not isinstance(last_message.content, types.TextContent):
        return []
    
    review_text = last_message.content.text
    comments = []
    
    # Try to extract file-specific comments
    current_file = None
    current_comments = []
    
    for line in review_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check for file path markers
        if line.startswith('File:'):
            # Save previous file's comments if any
            if current_file and current_comments:
                for comment in current_comments:
                    comments.append({
                        'path': current_file,
                        'line': comment.get('line', 1),
                        'message': comment['message']
                    })
            
            # Start new file
            current_file = line[5:].strip()
            current_comments = []
        elif line.startswith('- ') and current_file:
            # Extract line number if present (e.g., "Line 42: Some comment")
            line_content = line[2:].strip()
            line_match = re.match(r'^Line (\d+):\s*(.+)$', line_content)
            
            if line_match:
                line_num = int(line_match.group(1))
                message = line_match.group(2)
            else:
                line_num = 1
                message = line_content
            
            current_comments.append({
                'line': line_num,
                'message': message
            })
    
    # Add any remaining comments
    if current_file and current_comments:
        for comment in current_comments:
            comments.append({
                'path': current_file,
                'line': comment.get('line', 1),
                'message': comment['message']
            })
    
    # If no file-specific comments were found, treat the entire review as a global comment
    if not comments:
        comments.append({
            'path': 'GLOBAL',
            'line': 1,
            'message': review_text
        })
    
    return comments

# Prompt definitions

@app.prompt()
def review_commit_prompt() -> List[base.Message]:
    """Generate a prompt for reviewing a commit."""
    return [
        base.UserMessage(content="""You are a code reviewer. Review the provided code changes and provide constructive feedback.
For each file, format your review as follows:

`file/path/here`:
- Your first comment about this file
- Your second comment about this file
- etc.

Focus on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Documentation and readability

Keep comments concise and actionable. If a file has no significant issues, you can skip it.""")
    ]

@app.prompt()
def comment_issues_prompt():
    """Generate a prompt for commenting on issues in a commit."""
    return [
        base.UserMessage(content="""You are a code reviewer. Review the provided code changes and identify issues that need to be addressed.
For each file, format your comments as follows:

`file/path/here`:
- Your first issue or suggestion
- Your second issue or suggestion
- etc.

Focus on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Documentation and readability

Keep comments concise and actionable. If a file has no significant issues, you can skip it.""")
    ]

# Tool handlers

@app.tool("gerrit_get_commit_info")
async def get_commit_info(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Fetch commit information for the current revision of a change."""
    logger.info(f"Fetching commit info for change ID: {change_id}")
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    try:
        # Construct the full URL using the environment variable
        url = f"{gerrit_url}/changes/{change_id}/revisions/current/commit"
        
        # Call make_gerrit_request with the correct 'url' argument
        commit_data = await make_gerrit_request(
            url=url,
            method="GET",
            session=session
        )
        logger.info(f"Successfully fetched commit info for change ID: {change_id}")
        return commit_data
    except (GerritAPIError, ResourceNotFoundError) as e:
        logger.error(f"Error getting commit info: {str(e)}")
        raise  # Re-raise the specific error
    except Exception as e:
        logger.error(f"Unexpected error getting commit info: {str(e)}")
        raise GerritAPIError(f"Unexpected error getting commit info: {str(e)}")

@app.tool("gerrit_get_change_detail")
async def get_change_detail(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get detailed information about a change."""
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    try:
        logger.info(f"Fetching change detail for {change_id}...")
        # Construct the full URL using the environment variable
        url = f"{gerrit_url}/a/changes/{change_id}/detail" 
        change_data = await make_gerrit_request(url=url, session=session)
        logger.info("Successfully fetched change detail")
        return change_data
    except Exception as e:
        return format_error_response(e)

@app.tool("gerrit_get_commit_message")
async def get_commit_message(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get the commit message for the current revision of a change."""
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    try:
        logger.info(f"Fetching commit message for {change_id}...")
        # Construct the full URL using the environment variable
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/commit"
        commit_data = await make_gerrit_request(url=url, session=session)
        logger.info("Successfully fetched commit message")
        return {
            "subject": commit_data.get("subject"),
            "message": commit_data.get("message")
        }
    except Exception as e:
        return format_error_response(e)

@app.tool("gerrit_get_related_changes")
async def get_related_changes(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get related changes for the current revision of a change."""
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    revision_id = "current" # Always use current revision
    try:
        logger.info(f"Fetching related changes for {change_id} at revision {revision_id}...")
        # Construct the full URL using the environment variable
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/{revision_id}/related"
        related_data = await make_gerrit_request(url=url, session=session)
        logger.info("Successfully fetched related changes")
        return related_data
    except Exception as e:
        return format_error_response(e)

@app.tool("gerrit_get_file_list")
async def get_file_list(change_id: str, ctx: Context) -> Dict[str, Any]:
    """Get a detailed list of files for the current revision of a change."""
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    revision_id = "current" # Always use current revision
    try:
        logger.info(f"Fetching file list for {change_id} at revision {revision_id}...")
        # Construct the full URL using the environment variable
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/{revision_id}/files"
        files_data = await make_gerrit_request(url=url, session=session)
        
        # Filter out the /COMMIT_MSG file and format the response
        files = {path: info for path, info in files_data.items() if path != "/COMMIT_MSG"}
        logger.info("Successfully fetched file list")
        return {"files": files}
    except Exception as e:
        return format_error_response(e)

@app.tool("gerrit_get_file_diff")
async def get_file_diff(change_id: str, file_path: str, ctx: Context) -> Dict[str, Any]:
    """Get the diff for a specific file in the current revision of a change."""
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    diff_data = None # Initialize diff_data to avoid reference errors in exception logging
    try:
        logger.info(f"Fetching diff for {file_path} in change {change_id}...")
        encoded_path = quote(file_path, safe='')
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/files/{encoded_path}/diff?intraline=true&whitespace=ignore-all"
        diff_data = await make_gerrit_request(url=url, session=session)

        # --- Revised Diff Parsing Logic --- 
        line_changes = []
        line_num_a = 0 # Line numbers in the original file (parent)
        line_num_b = 0 # Line numbers in the new file (revision)

        if isinstance(diff_data, dict):
            content_blocks = diff_data.get('content', [])
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if isinstance(block, dict):
                        if 'ab' in block:
                            lines = block['ab']
                            for text in lines:
                                line_num_a += 1
                                line_num_b += 1
                                line_changes.append({
                                    'line_number': line_num_b, # Use new line number for comments
                                    'content': text,
                                    'type': 'common'
                                })
                        elif 'a' in block:
                            lines = block['a']
                            for text in lines:
                                line_num_a += 1
                                line_changes.append({
                                    'line_number': line_num_a, # Use old line number 
                                    'content': text,
                                    'type': 'removed'
                                })
                        elif 'b' in block:
                            lines = block['b']
                            for text in lines:
                                line_num_b += 1
                                line_changes.append({
                                    'line_number': line_num_b,
                                    'content': text,
                                    'type': 'added'
                                })
                        elif 'skip' in block:
                            num_skipped = block['skip']
                            line_num_a += num_skipped
                            line_num_b += num_skipped
                            # Optionally add skip marker if needed by consumer
                            # line_changes.append({'type': 'skip', 'count': num_skipped}) 
        # --- End Revised Diff Parsing Logic ---

        logger.info(f"Successfully fetched and parsed file diff with {len(line_changes)} processed lines")
        
        # Extract metadata safely
        metadata = diff_data.get('meta_a', {}) if diff_data.get('change_type') != 'ADDED' else {}
        metadata_b = diff_data.get('meta_b', {})

        return {
            "file_path": file_path,
            "line_changes": line_changes, # Use the correctly parsed list
            "metadata": {
                 # Provide more context if available
                "change_type": diff_data.get('change_type', 'MODIFIED'),
                "content_type_a": metadata.get('content_type', ''),
                "content_type_b": metadata_b.get('content_type', ''),
                "lines_inserted": diff_data.get('lines_inserted', 0),
                "lines_deleted": diff_data.get('lines_deleted', 0),
                "size_delta": diff_data.get('size_delta', 0),
            }
        }
    except Exception as e:
        logger.error(f"Error getting file diff for {file_path}: {str(e)}")
        # Log the raw diff data if available to help debug parsing issues
        if diff_data:
             logger.error(f"Raw diff data received: {str(diff_data)[:500]}...") 
        else:
             logger.error("No diff data received before error.")
        logger.error(traceback.format_exc())
        # Return a standard error format if possible
        return format_error_response(e)

@app.tool("gerrit_create_draft_comment")
async def gerrit_create_draft_comment(
    change_id: str, 
    file_path: str, 
    message: str, 
    ctx: Context, 
    line: int
) -> Dict[str, Any]:
    """Creates a new draft comment on a specific line in a file for the current revision.
    If line is -1, creates a global comment on the file without line number."""
    
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    revision_id = "current" # Use current revision

    try:
        comment_input = {
            "path": file_path,
            "message": message,
            "unresolved": "true"
        }

        # Handle line number, treating -1 as a special case for global comments
        if line != -1:
            try:
                line_int = int(line)
                comment_input["line"] = line_int
                log_target = f"at line {line_int}"
            except (ValueError, TypeError):
                raise ValueError(f"Invalid line number provided: {line}. Must be an integer.")
        else:
            log_target = "as global comment"

        logger.info(f"Creating draft comment on {file_path} {log_target} in change {change_id}...")
        
        # Use the PUT method for the /drafts endpoint
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/{revision_id}/drafts"
        
        # The create draft endpoint expects PUT, not POST
        result = await make_gerrit_request(
            url=url,
            method="PUT", 
            data=comment_input, 
            session=session
        )
        
        logger.info(f"Successfully created draft comment on {file_path} {log_target}")
        # The response is the created CommentInfo entity
        return {"success": True, "message": "Draft comment created successfully", "comment_info": result}
        
    except ValueError as ve:
         logger.error(f"Validation error creating draft comment: {ve}")
         # Format validation errors properly
         return {"success": False, **json.loads(format_error_response(ve))}
    except Exception as e:
        logger.error(f"Error creating draft comment for {file_path} on change {change_id}: {e}")
        logger.error(traceback.format_exc())
        try:
             error_dict = json.loads(format_error_response(e)) 
        except json.JSONDecodeError:
             error_dict = {"error": f"Failed to format error response for: {e}"}
        return {"success": False, **error_dict}

@app.tool("gerrit_set_review")
async def gerrit_set_review(
    change_id: str,
    code_review_label: int,
    ctx: Context
) -> Dict[str, Any]:
    """Submits all draft comments for a change and applies the specified Code-Review label.
    
    This tool publishes all draft comments that have been created and sets the Code-Review label.
    This tool can ONLY be invoked after users approve.
    
    Parameters:
        change_id (str): The ID of the change to review
        code_review_label (int): The value for the Code-Review label (-1 or -2)
            - Use -1 for non-critical issues (style, minor improvements)
            - Use -2 for critical issues (bugs, security issues, major design problems)
    
    Returns:
        Dict[str, Any]: The result of the review submission
    """
    session = ctx.request_context.lifespan_context['gerrit_session']
    gerrit_url = os.environ.get("GERRIT_URL")
    if not gerrit_url: raise ValueError("GERRIT_URL not set")
    revision_id = "current"  # Use current revision
    
    try:
        # Validate the code review label
        if code_review_label not in [-2, -1]:
            raise ValueError("code_review_label must be either -1 (non-critical issues) or -2 (critical issues)")
        
        logger.info(f"Submitting review for change {change_id} with Code-Review label {code_review_label}...")
        
        # Prepare the review input
        review_input = {
            "drafts": "PUBLISH_ALL_REVISIONS",  # Publish all draft comments
            "labels": {
                "Code-Review": code_review_label
            },
            "ignore_automatic_attention_set_rules": True,
            "add_to_attention_set": [],
            "remove_from_attention_set": [],
            "reviewers": []
        }
        
        # Construct the URL for the review endpoint
        url = f"{gerrit_url}/a/changes/{change_id}/revisions/{revision_id}/review"
        
        # Submit the review
        result = await make_gerrit_request(
            url=url,
            method="POST",
            data=review_input,
            session=session
        )
        
        logger.info(f"Successfully submitted review for change {change_id}")
        return {
            "success": True,
            "message": "Review submitted successfully",
            "review_result": result
        }
        
    except ValueError as ve:
        logger.error(f"Validation error submitting review: {ve}")
        return {"success": False, **json.loads(format_error_response(ve))}
    except Exception as e:
        logger.error(f"Error submitting review for change {change_id}: {e}")
        logger.error(traceback.format_exc())
        try:
            error_dict = json.loads(format_error_response(e))
        except json.JSONDecodeError:
            error_dict = {"error": f"Failed to format error response for: {e}"}
        return {"success": False, **error_dict}

def parse_args():
    parser = argparse.ArgumentParser(description="Gerrit Review Server")
    return parser.parse_args()

if __name__ == "__main__":
    app.run() 