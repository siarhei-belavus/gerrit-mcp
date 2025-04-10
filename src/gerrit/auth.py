"""Authentication utilities for the Gerrit API."""

import asyncio
import logging
import os
from typing import Optional

import aiohttp

# Set up logging
logger = logging.getLogger(__name__)


def get_auth_credentials(gerrit_url=None, username=None, api_token=None):
    """Retrieve Gerrit authentication credentials.

    Args:
    ----
        gerrit_url (str, optional): The Gerrit URL
        username (str, optional): The Gerrit username
        api_token (str, optional): The Gerrit API token

    Returns:
    -------
        Tuple[str, str, str]: A tuple containing (gerrit_url, username, api_token)

    Raises:
    ------
        ValueError: If any of the credentials are missing

    """
    # Use provided parameters or fall back to environment variables
    gerrit_url = gerrit_url or os.environ.get("GERRIT_URL")
    username = username or os.environ.get("GERRIT_USERNAME")
    api_token = api_token or os.environ.get("GERRIT_API_TOKEN")

    if not all([gerrit_url, username, api_token]):
        missing = []
        if not gerrit_url:
            missing.append("GERRIT_URL")
        if not username:
            missing.append("GERRIT_USERNAME")
        if not api_token:
            missing.append("GERRIT_API_TOKEN")
        raise ValueError(f"Missing required credentials: {', '.join(missing)}")

    if gerrit_url and gerrit_url.endswith("/"):
        gerrit_url = gerrit_url[:-1]

    return gerrit_url, username, api_token


def create_auth_session(gerrit_url, username, api_token):
    """Create an authenticated aiohttp session for Gerrit API requests.

    Args:
    ----
        gerrit_url (str): The Gerrit URL
        username (str): The Gerrit username
        api_token (str): The Gerrit API token

    Returns:
    -------
        aiohttp.ClientSession: An authenticated session

    Raises:
    ------
        ValueError: If authentication credentials are missing

    """
    if not all([gerrit_url, username, api_token]):
        raise ValueError("GERRIT_URL, GERRIT_USERNAME, and GERRIT_API_TOKEN must be provided.")

    logger.info(f"Creating authenticated session for {gerrit_url} with user: {username}")

    # Configure timeouts to prevent hanging
    timeout = aiohttp.ClientTimeout(
        total=30,  # Total timeout for the whole request
        connect=10,  # Timeout for connecting to the server
        sock_read=30,  # Timeout for reading data from the socket
        sock_connect=10,  # Timeout for connecting to the socket
    )

    auth = aiohttp.BasicAuth(username, api_token)
    session = aiohttp.ClientSession(
        auth=auth,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=timeout,
        # Retry on connection errors with back-off strategy
        connector=aiohttp.TCPConnector(
            limit=10,  # Maximum number of connections
            ttl_dns_cache=300,  # TTL for DNS cache in seconds
            limit_per_host=5,  # Maximum number of connections per host
            force_close=False,  # Close connection after each request
        ),
    )

    logger.info("Client session created with timeout and connection settings")
    return session


async def validate_auth(
    session: aiohttp.ClientSession,
    gerrit_url: Optional[str] = None,
    username: Optional[str] = None,
) -> bool:
    """Validate authentication credentials by making a test request.

    Args:
    ----
        session (aiohttp.ClientSession): The session to validate
        gerrit_url (str, optional): The Gerrit URL
        username (str, optional): The Gerrit username

    Returns:
    -------
        bool: True if authentication is valid, False otherwise

    """
    # If not provided, try to get credentials from environment
    if gerrit_url is None or username is None:
        try:
            gerrit_url, username, _ = get_auth_credentials()
        except ValueError as e:
            logger.error(f"Authentication validation failed: {e!s}")
            return False

    logger.info(f"Validating authentication to {gerrit_url} for user {username}")

    try:
        # Try to access the self account endpoint which requires authentication
        endpoint = f"{gerrit_url}/a/accounts/self"
        logger.info(f"Making GET request to {endpoint}")

        async with session.get(endpoint) as response:
            status = response.status
            logger.info(f"Received response with status {status}")

            if status == 200:
                logger.info("Authentication successful")
                return True
            logger.error(f"Authentication failed with status {status}")
            try:
                response_text = await response.text()
                logger.error(f"Response text: {response_text[:200]}")
            except Exception as e:
                logger.error(f"Could not read response text: {e!s}")

            return False
    except aiohttp.ClientConnectorError as e:
        logger.error(f"Connection error during authentication validation: {e!s}")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"Client error during authentication validation: {e!s}")
        return False
    except asyncio.TimeoutError:
        logger.error("Request timed out during authentication validation")
        return False
    except Exception as e:
        logger.error(f"Authentication validation failed with unexpected error: {e!s}")
        logger.exception("Traceback for authentication error:")
        return False
