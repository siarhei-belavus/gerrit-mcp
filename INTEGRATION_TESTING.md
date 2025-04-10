# Integration Testing for Gerrit AI Review MCP

This document provides instructions for setting up and running integration tests for the Gerrit AI Review MCP server.

## Prerequisites

Before running the integration tests, ensure you have:

1. Python 3.8+ installed
2. A valid Gerrit instance with API access
3. Proper credentials configured

## Setup

### 1. Configure Environment Variables

Create or update your `.env` file with the following variables:

```
GERRIT_URL=https://your-gerrit-instance.com
GERRIT_USERNAME=your_username
GERRIT_API_TOKEN=your_api_token
TEST_CHANGE_ID=project~change_number
```

Where:
- `GERRIT_URL` is the URL of your Gerrit instance
- `GERRIT_USERNAME` is your Gerrit username
- `GERRIT_API_TOKEN` is your Gerrit API token or password
- `TEST_CHANGE_ID` is a valid change ID in your Gerrit instance that will be used for testing

### 2. Install Dependencies

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### 3. Optional: Configure Test Behavior

You can set additional environment variables to control test behavior:

- `SKIP_COMMENT_TESTS=true` - Skip tests that create draft comments on Gerrit
- `SKIP_REVIEW_TESTS=true` - Skip tests that submit reviews to Gerrit

## Running the Tests

### Integration Test

To run the MCP server integration test:

```bash
python integration_test.py
```

This test:
1. Starts the MCP server as a subprocess
2. Connects to it via TCP using the MCP client
3. Tests all MCP tools with real Gerrit data
4. Properly cleans up resources when done

### Running Specific Tests

To run specific tests:

```bash
python -m unittest integration_test.TestMCPServer.test_get_commit_info
```

Replace `test_get_commit_info` with the name of the specific test you want to run.

## How The Tests Work

The integration test uses a subprocess approach:

1. The MCP server is started as a subprocess using `run_server.py`
2. The test connects to the server using the MCP client
3. Each test method tests a specific MCP tool
4. At the end, the server is properly terminated and resources are cleaned up

This approach avoids issues with circular imports and context managers by:
1. Running the server in its own process
2. Using the network interface (TCP) to communicate

## Understanding the Tests

The integration tests verify:

1. MCP server startup and connectivity
2. Tool functionality for retrieving change information:
   - `gerrit_get_commit_info` - Gets commit details
   - `gerrit_get_change_detail` - Gets change details
   - `gerrit_get_commit_message` - Gets commit message
   - `gerrit_get_related_changes` - Gets related changes
   - `gerrit_get_file_list` - Gets list of files
   - `gerrit_get_file_diff` - Gets diff for a specific file
3. Tool functionality for modifying changes:
   - `gerrit_create_draft_comment` - Creates a draft comment on a line
   - `gerrit_set_review` - Submits a review with Code-Review label

## Troubleshooting

### Server Start Failures

If the MCP server fails to start:

1. Check that your environment variables are correctly set
2. Ensure the `run_server.py` file is executable
3. Check log output for specific errors
4. Verify you don't have another server instance running on the same port (default: 5678)

### Authentication Errors

If you see authentication errors:

1. Verify your Gerrit credentials
2. Check if your API token has expired
3. Ensure you have proper permissions in Gerrit

### Connection Errors

If you see connection errors:

1. Check if the server is running (look for process and port usage)
2. Verify the host and port configuration
3. Check for firewall or network issues

### Test Failures

If specific tests fail:

1. Check if the test change ID exists and is accessible
2. Verify the file paths and line numbers in the log output
3. Look for specific error messages in the logs

## Adding New Tests

When adding new MCP tools to the server, follow these steps to add tests:

1. Add a new test method to the `TestMCPServer` class
2. Follow this pattern:

```python
def test_new_tool(self):
    """Test description."""
    logger.info("\nTesting new_tool...")
    
    async def run_test():
        result = await self.__class__.client.call_tool(
            "gerrit_new_tool",
            {"param": "value"}
        )
        
        self.assertIsNotNone(result)
        result_dict = json.loads(result[0].text)
        self.assertIsInstance(result_dict, dict)
        # Additional assertions...
        
        logger.info("✅ new_tool test passed")
        return result_dict
    
    return self._run_async_test(run_test())
```

## Continuous Integration

To integrate these tests in a CI pipeline:

1. Set up secret environment variables in your CI system
2. Run the integration test as part of your build process
3. Consider using the `SKIP_COMMENT_TESTS` and `SKIP_REVIEW_TESTS` flags to avoid affecting real Gerrit changes 