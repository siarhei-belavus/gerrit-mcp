"""
Gerrit API client package.
"""
from .models import (
    CommentRange,
    CommentInput,
    ReviewInput,
    Change,
    FileInfo,
    LineChange,
    FileDiff
)
from .api import (
    GerritAPIError,
    ResourceNotFoundError,
    get_commit_info,
    get_change_detail,
    get_commit_message,
    get_related_changes,
    get_file_list,
    get_file_diff,
    create_draft_comment,
    set_review,
    extract_change_id
)
from .auth import (
    get_auth_credentials,
    create_auth_session,
    validate_auth
)

__all__ = [
    # Exceptions
    'GerritAPIError',
    'ResourceNotFoundError',
    
    # Models
    'CommentRange',
    'CommentInput',
    'ReviewInput',
    'Change',
    'FileInfo',
    'LineChange',
    'FileDiff',
    
    # API Functions
    'get_commit_info',
    'get_change_detail',
    'get_commit_message',
    'get_related_changes',
    'get_file_list',
    'get_file_diff',
    'create_draft_comment',
    'set_review',
    'extract_change_id',
    
    # Auth Functions
    'get_auth_credentials',
    'create_auth_session',
    'validate_auth'
] 