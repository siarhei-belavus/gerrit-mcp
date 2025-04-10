"""Unit tests for the Gerrit API client."""

import pytest
from unittest.mock import patch, MagicMock

# The issue is that there's no GerritAPI class, only individual functions
from src.gerrit import (
    get_commit_info,
    get_change_detail,
    GerritAPIError,
    ResourceNotFoundError
)


@pytest.fixture
def gerrit_credentials():
    """Fixture for Gerrit credentials."""
    gerrit_url = "https://test-gerrit.example.com"
    username = "test-user"
    api_token = "test-token"
    return gerrit_url, username, api_token


@pytest.fixture
def mock_session():
    """Fixture for a mock session."""
    return MagicMock()


@pytest.fixture(autouse=True)
def auth_patch(gerrit_credentials):
    """Patch the auth credentials - autouse to ensure it's active for all tests."""
    gerrit_url, username, api_token = gerrit_credentials
    with patch('src.gerrit.auth.get_auth_credentials', return_value=(gerrit_url, username, api_token)):
        yield


@pytest.mark.asyncio
async def test_get_change_detail(mock_session, gerrit_credentials):
    """Test getting change details."""
    gerrit_url, username, api_token = gerrit_credentials
    
    # Patch at the point of use, within the test itself
    with patch('src.gerrit.api.get_auth_credentials', return_value=(gerrit_url, username, api_token)):
        # Configure mock to return a sample response
        with patch('src.gerrit.api.make_gerrit_request') as mock_make_request:
            mock_make_request.return_value = {
                "id": "project~branch~Id123",
                "project": "test-project",
                "branch": "main",
                "subject": "Test commit"
            }
            
            # Call the function
            result = await get_change_detail("123456", mock_session)
            
            # Check if make_gerrit_request was called with correct arguments
            mock_make_request.assert_called_once()
            
            # Instead of assuming arg positions, just verify that the expected values
            # are present in the args or kwargs
            call_args = mock_make_request.call_args
            all_args = list(call_args.args) + list(call_args.kwargs.values())
            
            expected_url = f"{gerrit_url}/a/changes/123456/detail"
            url_found = any(arg == expected_url for arg in all_args)
            session_found = mock_session in all_args
            
            assert url_found, f"Expected URL not found in call args: {call_args}"
            assert session_found, f"Session not found in call args: {call_args}"
            
            # Verify returned data
            assert result["id"] == "project~branch~Id123"
            assert result["project"] == "test-project"

    # Add more tests for other API functions as needed


if __name__ == '__main__':
    pytest.main() 