"""Gerrit API client package."""

from .api import (
    GerritAPIError,
    ResourceNotFoundError,
    create_draft_comment,
    extract_change_id,
    get_change_detail,
    get_commit_info,
    get_commit_message,
    get_file_diff,
    get_file_list,
    get_related_changes,
    set_review,
)
from .auth import create_auth_session, get_auth_credentials, validate_auth
from .models import Change, CommentInput, CommentRange, FileDiff, FileInfo, LineChange, ReviewInput

__all__ = [
    "Change",
    "CommentInput",
    # Models
    "CommentRange",
    "FileDiff",
    "FileInfo",
    # Exceptions
    "GerritAPIError",
    "LineChange",
    "ResourceNotFoundError",
    "ReviewInput",
    "create_auth_session",
    "create_draft_comment",
    "extract_change_id",
    # Auth Functions
    "get_auth_credentials",
    "get_change_detail",
    # API Functions
    "get_commit_info",
    "get_commit_message",
    "get_file_diff",
    "get_file_list",
    "get_related_changes",
    "set_review",
    "validate_auth",
]
