from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "done", "failed"]


class FileEntry(BaseModel):
    path: str
    loc: int


class AnalysisRun(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    repo_id: str
    status: RunStatus = "pending"
    error: Optional[str] = None
    py_file_count: int = 0
    total_file_count: int = 0
    files: list[FileEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}
