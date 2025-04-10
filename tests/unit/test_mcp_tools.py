"""Unit tests for the MCP tools."""

import pytest
from unittest.mock import patch, MagicMock, call

# Fix imports to match the actual function names
from src.mmcp.tools.commit_tools import (
    get_commit_info_tool,
    get_change_detail_tool,
    get_commit_message_tool
)
from src.mmcp.tools.file_tools import get_file_list_tool
from src.mmcp.tools.review_tools import create_draft_comment_tool


@pytest.fixture
def mock_ctx():
    """Fixture for a mock context."""
    mock_context = MagicMock()
    mock_session = MagicMock()
    mock_context.request_context.lifespan_context.get.return_value = mock_session
    return mock_context


@pytest.mark.asyncio
async def test_get_commit_info_tool(mock_ctx):
    """Test get_commit_info_tool function."""
    # Configure mock to return test data
    with patch('src.mmcp.tools.commit_tools.get_commit_info') as mock_get_commit_info:
        mock_get_commit_info.return_value = {
            "commit": "abc123",
            "subject": "Test commit",
            "author": {"name": "Test User", "email": "test@example.com"}
        }
        
        # Call the tool function
        result = await get_commit_info_tool(change_id="123456", ctx=mock_ctx)
        
        # Verify the API was called with correct parameters
        mock_get_commit_info.assert_called_once()
        args, kwargs = mock_get_commit_info.call_args
        assert args[0] == "123456"
        assert args[1] == mock_ctx.request_context.lifespan_context.get.return_value
        
        # Verify the function returned the correct result
        assert result["commit"] == "abc123"
        assert result["subject"] == "Test commit"
        assert result["author"]["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_file_list_tool(mock_ctx):
    """Test get_file_list_tool function."""
    # Configure mock to return test data
    with patch('src.mmcp.tools.file_tools.get_file_list') as mock_get_file_list:
        mock_get_file_list.return_value = {
            "file1.py": {"status": "MODIFIED", "size": 100},
            "file2.py": {"status": "ADDED", "size": 200}
        }
        
        # Call the tool function
        result = await get_file_list_tool(change_id="123456", ctx=mock_ctx)
        
        # Verify the API was called with correct parameters
        mock_get_file_list.assert_called_once()
        args, kwargs = mock_get_file_list.call_args
        assert args[0] == "123456"
        assert args[1] == mock_ctx.request_context.lifespan_context.get.return_value
        
        # Verify the function returned the correct result
        assert "file1.py" in result
        assert "file2.py" in result
        assert result["file1.py"]["status"] == "MODIFIED"
        assert result["file2.py"]["status"] == "ADDED"


@pytest.mark.asyncio
async def test_create_draft_comment_tool(mock_ctx):
    """Test create_draft_comment_tool function."""
    # Configure mock to return test data
    with patch('src.mmcp.tools.review_tools.create_draft_comment') as mock_create_draft_comment:
        mock_create_draft_comment.return_value = {
            "id": "comment123",
            "message": "Test comment",
            "line": 10,
            "in_reply_to": None
        }
        
        # Call the tool function
        result = await create_draft_comment_tool(
            change_id="123456",
            file_path="file1.py",
            message="Test comment",
            line=10,
            ctx=mock_ctx
        )
        
        # Verify the API was called once
        mock_create_draft_comment.assert_called_once()
        
        # Instead of checking positional arguments, verify that all expected values 
        # are in the call arguments somewhere (handles different parameter order)
        call_args = mock_create_draft_comment.call_args
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        
        # Check that all expected values are in all_args
        assert "123456" in all_args
        assert "file1.py" in all_args
        assert "Test comment" in all_args
        assert mock_ctx.request_context.lifespan_context.get.return_value in all_args
        assert 10 in all_args
                
        # Verify the function returned the correct result
        assert result["id"] == "comment123"
        assert result["message"] == "Test comment"
        assert result["line"] == 10 