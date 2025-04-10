#!/usr/bin/env python3
"""
Integration test for the Gerrit AI Review MCP server.

This test starts the MCP server as a subprocess and tests all MCP tools.

Usage:
    python integration_test.py
"""
import asyncio
import json
import logging
import os
import sys
import unittest
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test configuration
GERRIT_URL = os.environ.get("GERRIT_URL")
GERRIT_USERNAME = os.environ.get("GERRIT_USERNAME")
GERRIT_API_TOKEN = os.environ.get("GERRIT_API_TOKEN")
TEST_CHANGE_ID = os.environ.get("TEST_CHANGE_ID", "project~change_number")

# Default timeout for async operations (seconds)
ASYNC_TIMEOUT = 30


class TestMCPServer(unittest.TestCase):
    """Integration tests for the Gerrit MCP server."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the testing environment and initialize the client."""
        # Skip tests if credentials are missing
        if not all([GERRIT_URL, GERRIT_USERNAME, GERRIT_API_TOKEN]):
            raise unittest.SkipTest("Gerrit credentials not configured in environment")
        
        logger.info("Starting test setup...")
        logger.info(f"Using Gerrit URL: {GERRIT_URL}")
        logger.info(f"Using Username: {GERRIT_USERNAME}")
        logger.info(f"API Token: {'*' * 8}")
        logger.info(f"Test Change ID: {TEST_CHANGE_ID}")
        
        # Create a new event loop
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        
        # Store test state
        cls.test_file_path = None
        cls.test_line_change = None
        
        # Create server parameters for use in each test
        cls.server_params = StdioServerParameters(
            command=sys.executable,
            args=["src/mmcp/server.py"],
            env=dict(os.environ)
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up resources."""
        if hasattr(cls, 'loop'):
            cls.loop.close()
    
    def _run_async_test(self, coro):
        """Helper to run async tests with timeout."""
        try:
            return self.loop.run_until_complete(
                asyncio.wait_for(coro, timeout=ASYNC_TIMEOUT)
            )
        except asyncio.TimeoutError:
            self.fail(f"Test timed out after {ASYNC_TIMEOUT} seconds")
    
    def _check_for_error(self, result_dict):
        """Check if the result contains an error and handle it appropriately."""
        if isinstance(result_dict, dict) and 'error' in result_dict:
            error_msg = result_dict['error']
            logger.error(f"Server returned an error: {error_msg}")
            
            # Check for specific error conditions
            if "module 'asyncio' has no attribute 'timeout'" in error_msg:
                self.skipTest("Server error: asyncio.timeout not available. This may be due to Python version mismatch.")
            
            # Generic error case
            self.fail(f"Server error: {error_msg}")
            
        return result_dict
    
    # Define a sampling callback for use in all tests
    async def _sampling_callback(self, message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
        return types.CreateMessageResult(
            role="assistant",
            content=types.TextContent(
                type="text",
                text="Test response from sampling callback",
            ),
            model="test-model",
            stopReason="endTurn",
        )
        
    async def _call_tool_and_check_result(self, session: ClientSession, tool_name: str, tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """Calls a tool, extracts JSON content, and checks for errors."""
        logger.info(f"Calling {tool_name} with params: {tool_params}")
        result = await session.call_tool(tool_name, tool_params)
        
        logger.info(f"Received response from {tool_name} call")
        self.assertIsNotNone(result, f"Result from {tool_name} should not be None")
        
        # Extract content from the result object
        result_dict = None
        if hasattr(result, 'content') and result.content and hasattr(result.content[0], 'text'):
            content_data = result.content[0].text
            try:
                result_dict = json.loads(content_data)
            except json.JSONDecodeError as e:
                self.fail(f"Failed to decode JSON from {tool_name} result content: {content_data} - Error: {e}")
        elif isinstance(result, str): # Handle cases where result might be a JSON string directly
            try:
                result_dict = json.loads(result)
            except json.JSONDecodeError as e:
                self.fail(f"Failed to decode JSON string from {tool_name} result: {result} - Error: {e}")
        elif isinstance(result, dict): # Handle cases where result might already be a dict
             result_dict = result
        else:
            self.fail(f"Unexpected result type from tool {tool_name}: {type(result)}, value: {result}")

        # Check for errors in the parsed dictionary
        return self._check_for_error(result_dict)

    def test_get_commit_info(self):
        """Test retrieving commit info."""
        logger.info("\nTesting get_commit_info...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_commit_info",
                        {"change_id": TEST_CHANGE_ID}
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("commit", result_dict)
                    self.assertIn("parents", result_dict)
                    
                    logger.info("✅ get_commit_info test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_get_change_detail(self):
        """Test retrieving change details."""
        logger.info("\nTesting get_change_detail...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_change_detail",
                        {"change_id": TEST_CHANGE_ID}
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("id", result_dict)
                    self.assertIn("project", result_dict)
                    self.assertIn("subject", result_dict)
                    
                    logger.info("✅ get_change_detail test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_get_commit_message(self):
        """Test retrieving commit message."""
        logger.info("\nTesting get_commit_message...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_commit_message",
                        {"change_id": TEST_CHANGE_ID}
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("message", result_dict)
                    
                    logger.info("✅ get_commit_message test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_get_related_changes(self):
        """Test retrieving related changes."""
        logger.info("\nTesting get_related_changes...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_related_changes",
                        {"change_id": TEST_CHANGE_ID}
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("changes", result_dict)
                    
                    logger.info("✅ get_related_changes test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_get_file_list(self):
        """Test retrieving file list."""
        logger.info("\nTesting get_file_list...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_file_list",
                        {"change_id": TEST_CHANGE_ID}
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("files", result_dict)
                    
                    # Store a file path for later tests
                    if result_dict.get("files") and isinstance(result_dict["files"], dict) and result_dict["files"]:
                        self.__class__.test_file_path = next(iter(result_dict["files"].keys()))
                        logger.info(f"Selected test file path: {self.__class__.test_file_path}")
                    
                    logger.info("✅ get_file_list test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_get_file_diff(self):
        """Test retrieving file diff."""
        logger.info("\nTesting get_file_diff...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Get file list if we don't have a file path yet
                    if not self.__class__.test_file_path:
                        file_list_dict = await self._call_tool_and_check_result(
                            session,
                            "gerrit_get_file_list",
                            {"change_id": TEST_CHANGE_ID}
                        )
                        
                        if not file_list_dict or not file_list_dict.get("files") or not isinstance(file_list_dict["files"], dict) or not file_list_dict["files"]:
                            self.skipTest("No files available to test file diff")
                        self.__class__.test_file_path = next(iter(file_list_dict["files"].keys()))
                    
                    logger.info(f"\nTesting get_file_diff for {self.__class__.test_file_path}...")
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_get_file_diff",
                        {
                            "change_id": TEST_CHANGE_ID,
                            "file_path": self.__class__.test_file_path
                        }
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    
                    # Store the test data for subsequent comment tests
                    if "line_changes" in result_dict and result_dict["line_changes"]:
                        self.__class__.test_line_change = result_dict["line_changes"][0]
                    
                    logger.info("✅ get_file_diff test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    @unittest.skipIf(os.environ.get("SKIP_COMMENT_TESTS", "false").lower() == "true", 
                    "Skipping comment creation tests")
    def test_create_draft_comment(self):
        """Test creating a draft comment."""
        logger.info("\nTesting create_draft_comment...")
        
        async def run_test():
            # Skip if no line change is available
            if not self.__class__.test_line_change or not self.__class__.test_file_path:
                self.skipTest("No line changes available to test comment creation")
            
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    line_number = self.__class__.test_line_change.get("line_number", 1)
                    logger.info(f"\nTesting create_draft_comment on {self.__class__.test_file_path}:{line_number}...")
                    
                    comment_text = "AI integration test: This is a test comment. Please ignore."
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_create_draft_comment",
                        {
                            "change_id": TEST_CHANGE_ID,
                            "file_path": self.__class__.test_file_path,
                            "line": line_number,
                            "message": comment_text
                        }
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("success", result_dict)
                    self.assertTrue(result_dict["success"])
                    
                    logger.info("✅ create_draft_comment test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    @unittest.skipIf(os.environ.get("SKIP_REVIEW_TESTS", "false").lower() == "true", 
                    "Skipping review submission tests")
    def test_set_review(self):
        """Test submitting a review with Code-Review label."""
        logger.info("\nTesting set_review...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Note: In a real scenario, you would first create draft comments
                    # We're just testing the API call here with a separate message
                    
                    result_dict = await self._call_tool_and_check_result(
                        session,
                        "gerrit_set_review",
                        {
                            "change_id": TEST_CHANGE_ID,
                            "code_review_label": -1
                        }
                    )
                    
                    self.assertIsInstance(result_dict, dict)
                    self.assertIn("labels", result_dict)
                    self.assertIsInstance(result_dict["labels"], dict)
                    self.assertIn("Code-Review", result_dict["labels"])
                    self.assertEqual(result_dict["labels"]["Code-Review"], -1)
                    
                    logger.info("✅ set_review test passed")
                    return result_dict
        
        return self._run_async_test(run_test())
    
    def test_list_tools(self):
        """Test listing available tools."""
        logger.info("\nTesting list_tools...")
        
        async def run_test():
            async with stdio_client(self.__class__.server_params) as (read, write):
                async with ClientSession(
                    read, write, sampling_callback=self._sampling_callback
                ) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    tools_result = await session.list_tools()
                    
                    self.assertIsNotNone(tools_result)
                    logger.info(f"Tools result type: {type(tools_result)}")
                    
                    # Tools result is already an object, extract the list of tools
                    if hasattr(tools_result, 'tools'):
                        tools = tools_result.tools
                    else:
                        tools = tools_result
                    
                    self.assertTrue(len(tools) > 0)
                    
                    # Verify some expected tools are present
                    tool_names = [tool.name for tool in tools]
                    logger.info(f"Available tools: {', '.join(tool_names)}")
                    
                    expected_tools = [
                        "gerrit_get_commit_info",
                        "gerrit_get_change_detail",
                        "gerrit_get_file_list"
                    ]
                    
                    for tool in expected_tools:
                        self.assertIn(tool, tool_names, f"Expected tool '{tool}' not found")
                    
                    logger.info("✅ list_tools test passed")
                    return tools
        
        return self._run_async_test(run_test())


if __name__ == "__main__":
    unittest.main() 