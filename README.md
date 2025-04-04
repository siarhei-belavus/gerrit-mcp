# Gerrit AI Review MCP

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
pip install git+https://github.com/siarhei-belavus/gerrt_ai_review.git
```

Or, for development:

1. Clone the repository:
```bash
git clone git@github.com:siarhei-belavus/gerrt_ai_review.git
cd gerrit_ai_review
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

## Configuration

Create a `.env` file with your Gerrit credentials:
```
GERRIT_URL=your_gerrit_url
GERRIT_USERNAME=your_username
GERRIT_API_TOKEN=your_api_token
```

## Cursor IDE Integration

To integrate this MCP server with Cursor IDE:

1. Make the wrapper script executable:
```bash
chmod +x gerrit_mcp.sh
```

2. Configure the MCP server in Cursor by creating/editing `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "gerrit-ai-review": {
      "command": "/absolute/path/to/gerrit_ai_review/gerrit_mcp.sh",
      "env": {
        "GERRIT_URL": "your_gerrit_url",
        "GERRIT_USERNAME": "your_username",
        "GERRIT_API_TOKEN": "your_api_token"
      }
    }
  }
}
```

You can also use project-specific configuration by placing the `mcp.json` file in your project's `.cursor` directory.

## Usage

1. If installed via pip, run:
```bash
gerrit-ai-review
```

Or if running from source:
```bash
python src/server_direct.py
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

```bash
python test_server.py
```

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