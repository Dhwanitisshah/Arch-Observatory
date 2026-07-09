from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Repo(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    url: str
    owner: str
    name: str
    default_branch: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}
