from __future__ import annotations

from pydantic import BaseModel, Field


class LogFileInfo(BaseModel):
    name: str
    size_bytes: int
    modified_at: str | None = None
    is_current: bool


class LogViewerResponse(BaseModel):
    files: list[LogFileInfo] = Field(default_factory=list)
    selected_file: str | None = None
    line_limit: int
    total_lines: int
    truncated: bool
    lines: list[str] = Field(default_factory=list)
    fetched_at: str
