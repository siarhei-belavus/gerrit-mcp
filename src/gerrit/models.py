"""Data models and type definitions for the Gerrit API.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class CommentRange:

    """Range for a Gerrit comment."""

    start_line: int
    start_character: int
    end_line: int
    end_character: int


@dataclass
class CommentInput:

    """Input data for creating a Gerrit comment."""

    message: str
    path: str
    line: Optional[int] = None
    range: Optional[CommentRange] = None
    in_reply_to: Optional[str] = None
    unresolved: Optional[bool] = None
    side: Literal["REVISION", "PARENT"] = "REVISION"


@dataclass
class ReviewInput:

    """Input data for submitting a Gerrit review."""

    message: Optional[str] = None
    labels: Optional[Dict[str, int]] = None
    comments: Optional[Dict[str, List[CommentInput]]] = None
    drafts: Literal["PUBLISH", "PUBLISH_ALL_REVISIONS", "KEEP"] = "PUBLISH"


@dataclass
class Change:

    """Gerrit change information."""

    id: str
    project: str
    branch: str
    topic: Optional[str] = None
    change_id: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    owner: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    current_revision: Optional[str] = None
    revisions: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None


@dataclass
class FileInfo:

    """Information about a file in a Gerrit change."""

    status: str
    lines_inserted: Optional[int] = None
    lines_deleted: Optional[int] = None
    size_delta: Optional[int] = None
    size: Optional[int] = None
    binary: Optional[bool] = None


@dataclass
class LineChange:

    """Represents a changed line in a file diff."""

    type: Literal["added", "removed", "common"]
    line_number: int
    content: str


@dataclass
class FileDiff:

    """Represents a diff for a specific file."""

    file_path: str
    old_path: Optional[str] = None
    line_changes: List[LineChange] = field(default_factory=list)
    is_binary: bool = False
    content_type: Optional[str] = None
