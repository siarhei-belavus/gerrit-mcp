"""
Gerrit REST API client implementation.
"""
import re
import json
import logging
from typing import Dict, List, Optional, Any, Union, TypeVar, Callable, Awaitable
import functools
import aiohttp
from urllib.parse import urlparse, parse_qs, quote
import asyncio
import uuid

from .auth import get_auth_credentials

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


class GerritAPIError(Exception):
    """Custom exception for Gerrit API errors."""
    pass


class ResourceNotFoundError(GerritAPIError):
    """Custom exception for when a Gerrit resource is not found."""
    pass


def parse_gerrit_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the Gerrit API response, handling the magic prefix.
    
    Args:
        response_text (str): The raw response text from the Gerrit API
        
    Returns:
        Dict[str, Any]: The parsed JSON response
        
    Raises:
        GerritAPIError: If the response cannot be parsed as JSON
    """
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


def handle_gerrit_errors(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[Union[T, Dict[str, str]]]]:
    """
    Decorator to consistently handle errors in Gerrit API calls.
    
    Args:
        func: The async function to wrap
        
    Returns:
        The wrapped function that handles errors
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Union[T, Dict[str, str]]:
        try:
            return await func(*args, **kwargs)
        except ResourceNotFoundError as e:
            logger.error(f"Resource not found: {str(e)}")
            return {"error": f"Resource not found: {str(e)}"}
        except GerritAPIError as e:
            logger.error(f"Gerrit API error: {str(e)}")
            return {"error": f"Gerrit API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    return wrapper


async def make_gerrit_request(
    url: str, 
    session: aiohttp.ClientSession,
    method: str = "GET", 
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Make a request to the Gerrit API with proper error handling.
    
    Args:
        url (str): The FULL URL to make the request to (already processed)
        session (aiohttp.ClientSession): The aiohttp session to use
        method (str, optional): The HTTP method to use. Defaults to "GET".
        data (Optional[Dict[str, Any]], optional): The data to send with the request. Defaults to None.
        timeout (int, optional): Request timeout in seconds. Defaults to 30.
        
    Returns:
        Dict[str, Any]: The parsed response from the Gerrit API
        
    Raises:
        ResourceNotFoundError: If the resource is not found (404)
        GerritAPIError: If any other error occurs during the request
    """
    try:
        # URL processing logic remains, but assumes `url` might contain the base path
        # It now needs the base gerrit_url to correctly encode change IDs relative to the base
        # Let's fetch it here just for the encoding logic, assuming it's consistent
        # A better approach might be to pass base_gerrit_url explicitly if needed for encoding.
        base_gerrit_url, _, _ = get_auth_credentials() # Get base URL just for path manipulation

        processed_url = url  # Start with the original URL passed in
        
        if '/changes/' in url:
            logger.debug(f"Processing URL containing /changes/: {url}")
            
            # Extract the change ID part relative to the base Gerrit URL
            if url.startswith(base_gerrit_url):
                relative_path = url[len(base_gerrit_url):].lstrip('/')
                path_parts_from_base = relative_path.split('/')
                
                try:
                    changes_index = path_parts_from_base.index('changes')
                    if changes_index + 1 < len(path_parts_from_base):
                        change_id_part = path_parts_from_base[changes_index + 1]
                        remaining_path_parts = path_parts_from_base[changes_index + 2:]
                        remaining_path = '/'.join(remaining_path_parts) if remaining_path_parts else ''
                        
                        original_change_id = change_id_part
                        encoded_change_id_part = change_id_part
                        if '~' in change_id_part:
                            parts = change_id_part.split('~')
                            if len(parts) == 2:
                                project, number = parts
                                encoded_change_id_part = f"{quote(project, safe='')}~{number}"
                            else:
                                encoded_change_id_part = '~'.join(quote(p, safe='') for p in parts)
                        elif not change_id_part.isdigit():
                            encoded_change_id_part = quote(change_id_part, safe='')

                        # Reconstruct the URL ensuring /a/ prefix
                        prefix = "/a/" # Assume authenticated requests need /a/
                        processed_url = f"{base_gerrit_url}{prefix}changes/{encoded_change_id_part}"
                        if remaining_path:
                            processed_url = f"{processed_url}/{remaining_path}"
                        logger.debug(f"Reconstructed URL for change ID: {processed_url}")
                    else:
                        logger.warning(f"Could not extract change ID part from URL: {url}")
                except ValueError:
                    logger.warning(f"'changes' segment not found in URL path: {url}")
            else:
                logger.warning(f"URL {url} does not start with expected base Gerrit URL {base_gerrit_url}")
        else:
            # Ensure /a/ prefix for other authenticated endpoints if needed
            if base_gerrit_url and url.startswith(base_gerrit_url) and '/a/' not in url:
                 # Avoid adding /a/ if it's something like /login/
                 if not url.endswith("/login/") and not url.endswith("/config/server/version") :
                    relative_path = url[len(base_gerrit_url):].lstrip('/')
                    if not relative_path.startswith('a/'): 
                        processed_url = f"{base_gerrit_url}/a/{relative_path}"
                        logger.debug(f"Added /a/ prefix for non-changes URL: {processed_url}")

        # Final check if /a/ is needed before /changes/
        if '/changes/' in processed_url and '/a/changes/' not in processed_url:
             processed_url = processed_url.replace('/changes/', '/a/changes/')
             logger.debug(f"Ensured /a/ prefix for changes URL: {processed_url}")

        logger.info(f"Making {method} request to final URL: {processed_url}")
        if data:
            logger.debug(f"Request Data: {json.dumps(data)}")  # Log POST/PUT data

        try:
            # Use asyncio.wait_for for compatibility with Python < 3.11
            response_task = asyncio.create_task(session.request(method, processed_url, json=data))
            done, pending = await asyncio.wait({response_task}, timeout=timeout)
            
            if response_task in pending:
                response_task.cancel()
                try:
                    await response_task # Allow cancellation to propagate
                except asyncio.CancelledError:
                    logger.error(f"Request to {processed_url} timed out after {timeout} seconds (using wait_for)")
                    raise GerritAPIError(f"Request timed out after {timeout} seconds")
            
            if response_task in done:
                # If the task finished, get the result (which is the context manager for the response)
                response_cm = response_task.result() 
                async with response_cm as response:
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
            else: # Should not happen with wait, but handle defensively
                 raise GerritAPIError("Task finished but was not in the 'done' set")
        except asyncio.TimeoutError: # This might still be raised by wait_for internals or if wait itself times out
            logger.error(f"Request to {processed_url} timed out after {timeout} seconds")
            raise GerritAPIError(f"Request timed out after {timeout} seconds")
            
    except aiohttp.ClientConnectorError as e:
        logger.error(f"Connection error connecting to {processed_url}: {str(e)}")
        raise GerritAPIError(f"Connection error: {str(e)}")
    except aiohttp.ClientError as e:
        logger.error(f"Client error requesting {processed_url}: {str(e)}")
        raise GerritAPIError(f"Client error: {str(e)}")
    except json.JSONDecodeError as e:  # Should be caught by parse_gerrit_response, but as fallback
        logger.error(f"Invalid JSON response from {processed_url}: {str(e)}")
        raise GerritAPIError(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        if isinstance(e, (ResourceNotFoundError, GerritAPIError)):
            raise  # Re-raise specific known errors
        logger.error(f"Unexpected error during Gerrit request to {processed_url}: {str(e)}")
        logger.exception("Traceback for unexpected error:")  # Log full traceback
        raise GerritAPIError(f"Unexpected error: {str(e)}")


def extract_change_id(commit_url: str) -> Optional[str]:
    """
    Extract the change ID from a Gerrit commit URL.
    
    Args:
        commit_url (str): The Gerrit commit URL
        
    Returns:
        Optional[str]: The extracted change ID, or None if not found
    """
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
        logger.error(f"Error extracting change ID from URL {commit_url}: {str(e)}")
        return None


@handle_gerrit_errors
async def get_commit_info(
    change_id: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/commit" # Construct full URL
    return await make_gerrit_request(url, session=session)


@handle_gerrit_errors
async def get_change_detail(
    change_id: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    url = f"{gerrit_url}/a/changes/{change_id}/detail" # Construct full URL
    return await make_gerrit_request(url, session=session)


@handle_gerrit_errors
async def get_commit_message(
    change_id: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    # Note: This endpoint typically doesn't require /a/ prefix for public changes
    url = f"{gerrit_url}/changes/{change_id}/revisions/current/commit" # Construct full URL
    return await make_gerrit_request(url, session=session)


@handle_gerrit_errors
async def get_related_changes(
    change_id: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/related" # Construct full URL
    return await make_gerrit_request(url, session=session)


@handle_gerrit_errors
async def get_file_list(
    change_id: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/files" # Construct full URL
    result = await make_gerrit_request(url, session=session)
    
    # Filter out the commit message pseudo-file
    if isinstance(result, dict) and '/COMMIT_MSG' in result:
        del result['/COMMIT_MSG']
    
    # Transform the response for easier consumption
    return {
        "files": result if isinstance(result, dict) else {}
    }


@handle_gerrit_errors
async def get_file_diff(
    change_id: str,
    file_path: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    
    # Encode file path for URL
    encoded_file_path = quote(file_path, safe='')
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/files/{encoded_file_path}/diff" # Construct full URL
    
    raw_diff = await make_gerrit_request(url, session=session)
    
    # Check if this is a binary file
    if raw_diff.get('binary', False):
        return {
            "file_path": file_path,
            "is_binary": True,
            "content_type": raw_diff.get('content_type', None),
            "line_changes": []
        }
    
    # Process the diff content to extract line changes
    line_changes = []
    current_line = 1
    
    # Process the content sections (common, added, removed)
    for section in raw_diff.get('content', []):
        lines = section.get('ab', [])  # Common lines
        if lines:
            for line in lines:
                line_changes.append({
                    "type": "common",
                    "line_number": current_line,
                    "content": line
                })
                current_line += 1
        
        # Added lines
        lines = section.get('b', [])
        if lines:
            for line in lines:
                line_changes.append({
                    "type": "added",
                    "line_number": current_line,
                    "content": line
                })
                current_line += 1
        
        # Removed lines do not increment the current line counter
        lines = section.get('a', [])
        if lines:
            for line in lines:
                line_changes.append({
                    "type": "removed",
                    "line_number": current_line - 1,  # Use previous line number
                    "content": line
                })
    
    return {
        "file_path": file_path,
        "is_binary": False,
        "line_changes": line_changes
    }


@handle_gerrit_errors
async def create_draft_comment(
    change_id: str,
    file_path: str,
    message: str,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession,
    line: int # Use -1 for file-level comment
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    
    # Prepare the comment data (CommentInput entity format)
    comment_data = {
        "path": file_path,
        "message": message,
        "unresolved": True # Changed from string "true"
    }
    
    if line != -1:
        comment_data["line"] = line
    
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/drafts" # Construct full URL

    return await make_gerrit_request(
        url,
        session=session,
        method="PUT",
        data=comment_data
    )


@handle_gerrit_errors
async def set_review(
    change_id: str,
    code_review_label: int,
    gerrit_url: str, # Added parameter
    session: aiohttp.ClientSession,
    message: Optional[str] = None
) -> Dict[str, Any]:
    # Removed: gerrit_url, username, api_token = get_auth_credentials(gerrit_url, username, api_token)
    
    # Validate the code review label
    if code_review_label not in [-1, -2]:
        error_msg = f"Invalid Code-Review label value: {code_review_label}. Must be -1 or -2."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Prepare the review data
    review_data = {
        "drafts": "PUBLISH",
        "labels": {
            "Code-Review": code_review_label
        }
    }
    
    if message:
        review_data["message"] = message
    
    url = f"{gerrit_url}/a/changes/{change_id}/revisions/current/review" # Construct full URL
    
    return await make_gerrit_request(
        url,
        session=session,
        method="POST",
        data=review_data
    ) 