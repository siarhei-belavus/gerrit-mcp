#!/usr/bin/env python3
"""Test runner for Gerrit AI Review MCP.
Run unit tests with:
    python run_tests.py
"""

import sys

import pytest

if __name__ == "__main__":
    # Use pytest to handle async tests properly
    sys.exit(pytest.main(["-v", "tests/unit"]))
