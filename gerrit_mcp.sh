#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
  source "$SCRIPT_DIR/venv/bin/activate"
else
  echo "Virtual environment not found at $SCRIPT_DIR/venv"
  exit 1
fi

# --- Configuration Loading ---
# Default values (can be overridden by .env or command line)
USERNAME=""
API_TOKEN=""
GERRIT_URL=""

# Load from .env file if it exists in the script directory
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  echo "Loading configuration from $ENV_FILE"
  # Use set -a to export variables read from .env
  set -a
  source "$ENV_FILE"
  set +a
  # Assign to script variables from potentially exported env vars
  USERNAME=${GERRIT_USERNAME:-$USERNAME}
  API_TOKEN=${GERRIT_API_TOKEN:-$API_TOKEN}
  GERRIT_URL=${GERRIT_URL:-$GERRIT_URL}
fi

# Parse command line arguments (override .env file settings)
while [[ $# -gt 0 ]]; do
  case $1 in
    --username=*) USERNAME="${1#*=}"; shift ;; 
    --api-token=*) API_TOKEN="${1#*=}"; shift ;; 
    --gerrit-url=*) GERRIT_URL="${1#*=}"; shift ;; 
    *)
      echo "Unknown option: $1"
      # Optionally, pass unknown args to the python script
      # PYTHON_ARGS+=("$1") 
      shift
      ;;
  esac
done

# Check if required variables are set
if [ -z "$USERNAME" ] || [ -z "$API_TOKEN" ] || [ -z "$GERRIT_URL" ]; then
  echo "Error: Missing required configuration."
  echo "Please ensure GERRIT_USERNAME, GERRIT_API_TOKEN, and GERRIT_URL are set"
  echo "either in $ENV_FILE or via command line arguments (--username, --api-token, --gerrit-url)."
  exit 1
fi

# Export variables for the Python script to use (via os.environ)
export GERRIT_USERNAME="$USERNAME"
export GERRIT_API_TOKEN="$API_TOKEN"
export GERRIT_URL="$GERRIT_URL"

# --- Run Server ---
echo "Starting MCP server for Gerrit URL: $GERRIT_URL with user: $USERNAME"
# Run the MCP server (no longer needs command line args for config)
python "$SCRIPT_DIR/src/server_direct.py" 