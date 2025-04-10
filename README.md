# Gerrit AI Review MCP

[![Build and Test](https://github.com/siarhei-belavus/gerrit-mcp/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/siarhei-belavus/gerrit-mcp/actions/workflows/build_and_test.yml)

A Model Context Protocol (MCP) server implementation that integrates Gerrit code reviews with AI-powered IDEs like Cursor. This server enables automated code reviews by connecting your Gerrit instance with AI capabilities through the MCP protocol.

## Features

- **MCP Server Implementation:**
  - Built using the MCP Python SDK
  - Exposes Gerrit functionality through MCP tools
  - Seamless integration with AI-powered IDEs

- **Gerrit Integration:**
  - Fetch commit information and change details
  - Create and manage draft comments
  - Support for line-specific and global comments
  - Apply Code-Review labels (-1 or -2)
  - Authenticated Gerrit REST API interaction

- **Available Tools:**
  - `gerrit_get_commit_info`: Fetch basic commit information
  - `gerrit_get_change_detail`: Retrieve detailed change information
  - `gerrit_get_commit_message`: Get commit messages
  - `gerrit_get_related_changes`: Find related changes
  - `gerrit_get_file_list`: List modified files
  - `gerrit_get_file_diff`: Get file-specific diffs
  - `gerrit_create_draft_comment`: Create draft comments
  - `gerrit_set_review`: Submit reviews with labels

## Installation

You can install this package directly from GitHub using pip:

```bash
pip install git+https://github.com/siarhei-belavus/gerrit-mcp.git
```

Or, for development:

1. Clone the repository:
```bash
git clone git@github.com:siarhei-belavus/gerrit-mcp.git
cd gerrit-mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .
```

## Configuration Options

### Environment Variables

The repository includes an `.env.template` file that you can copy and modify:
```bash
cp .env.template .env
```

Then edit the `.env` file with your Gerrit credentials:
```
GERRIT_URL=your_gerrit_url
GERRIT_USERNAME=your_username
GERRIT_API_TOKEN=your_api_token
```

### Command-Line Arguments

Alternatively, you can use command-line arguments when running the server:
```bash
GERRIT_URL=your_gerrit_url
GERRIT_USERNAME=your_username
GERRIT_API_TOKEN=your_api_token
```

## Project Structure

The project follows a modular architecture:

```
src/
├── gerrit/             # Gerrit API client
│   ├── api.py          # API request functions
│   ├── auth.py         # Authentication utilities
│   └── models.py       # Data models
├── mcp/                # MCP server implementation
│   ├── server.py       # Server setup
│   └── tools/          # MCP tool implementations
│       ├── commit_tools.py    # Commit-related tools
│       ├── file_tools.py      # File-related tools
│       └── review_tools.py    # Review and comment tools
└── utils/              # Utility functions
    ├── error_handling.py  # Error handling utilities
    └── logging.py         # Logging utilities
```

## Cursor IDE Integration

To integrate this MCP server with Cursor IDE:

1. Install the package:
```bash
pip install git+https://github.com/siarhei-belavus/gerrit-mcp.git
```

2. Configure the MCP server in Cursor by creating/editing `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "gerrit-mcp": {
      "command": "gerrit-mcp",
      "workingDirectory": "path/to/working/directory",
      "env": {
        "GERRIT_URL": "your_gerrit_url",
        "GERRIT_USERNAME": "your_username",
        "GERRIT_API_TOKEN": "your_api_token"
      }
    }
  }
}
```

### Alternative Configuration with Command Arguments

If you prefer to use command-line arguments instead of environment variables:

```json
{
  "mcpServers": {
    "gerrit-mcp": {
      "command": "gerrit-mcp --gerrit_url your_gerrit_url --username your_username --api_token your_api_token",
      "workingDirectory": "path/to/working/directory",
      "env": {}
    }
  }
}
```

Using environment variables is generally preferred for credentials since they:
- Don't appear in process listings (like when running `ps aux`)
- Aren't stored in command history
- Are easier to manage with credential management systems

You can also use project-specific configuration by placing the `mcp.json` file in your project's `.cursor` directory.

For development from source, use the full path to the script:
```json
{
  "mcpServers": {
    "gerrit-mcp": {
      "command": "/absolute/path/to/gerrit-mcp/gerrit_mcp.sh",
      "workingDirectory": "path/to/working/directory",
      "env": {}
    }
  }
}
```

## Usage

1. If installed via pip, run:
```bash
gerrit-mcp
```

Or if running from source:
```bash
python src/server.py
```

Command line options:
```
--host HOST           Host to bind the server to (default: 127.0.0.1)
--port PORT           Port to bind the server to (default: 5678)
--debug               Enable debug logging
--log-file LOG_FILE   Path to log file (default: logs to stdout)

# Authentication options (when not using environment variables)
--gerrit_url URL      Gerrit server URL
--username USERNAME   Gerrit username
--api_token TOKEN     Gerrit API token or password

For complete usage information, run: gerrit-mcp --help
```

2. In Cursor IDE:
   - Open a conversation about a Gerrit review
   - Paste a Gerrit change URL
   - Ask Cursor to review the changes using the available tools
   - Approve comments to be posted back to Gerrit

Example prompts:
- "Review this Gerrit change for issues"
- "Create draft comments for the problematic areas"
- "Submit the review with appropriate labels"

## Development

### Prerequisites

- Python 3.8 or higher
- Git
- Access to a Gerrit instance

### Running Tests

For unit tests (which can run without a Gerrit instance):
```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
python -m pytest tests/unit -v
```

For integration tests (requires connection to a Gerrit instance):
```bash
python tests/integration_test.py
```

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install the package in development mode
pip install -e .
```

### Continuous Integration

This repository uses GitHub Actions for continuous integration, which automatically:
- Lints the code with Ruff
- Runs unit tests with pytest
- Builds the package

The workflow runs on every push to the main branch and on pull requests.

### Building from Source

1. Install build requirements:
```bash
pip install build
```

2. Build the package:
```bash
python -m build
```

This will create distribution files in the `dist/` directory.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.