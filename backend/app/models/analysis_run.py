from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "done", "failed"]


class FunctionEntry(BaseModel):
    name: str
    type: str
    lineno: int
    endline: Optional[int] = None
    complexity: int
    classname: Optional[str] = None


class FileEntry(BaseModel):
    path: str
    loc: int
    parse_ok: bool = True
    error: Optional[str] = None
    lloc: Optional[int] = None
    sloc: Optional[int] = None
    comments: Optional[int] = None
    blank: Optional[int] = None
    mi: Optional[float] = None
    halstead_volume: Optional[float] = None
    halstead_difficulty: Optional[float] = None
    functions: list[FunctionEntry] = Field(default_factory=list)
    max_complexity: int = 0
    avg_complexity: float = 0


class HighComplexityFunction(BaseModel):
    path: str
    name: str
    classname: Optional[str] = None
    complexity: int
    lineno: int


class DependencyNode(BaseModel):
    module: str
    path: str
    ca: int
    ce: int
    instability: float


class DependencyEdge(BaseModel):
    source: str
    target: str


class DependencyCycle(BaseModel):
    members: list[str]
    concrete_cycles: list[list[str]]


class MostDependedOn(BaseModel):
    module: str
    ca: int


class MostUnstable(BaseModel):
    module: str
    instability: float
    ce: int


class SmellModel(BaseModel):
    type: str
    severity: float
    target: str
    path: str
    title: str
    detail: str
    metrics: dict = Field(default_factory=dict)


class AnalysisRun(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    repo_id: str
    status: RunStatus = "pending"
    stage: Optional[str] = None
    error: Optional[str] = None
    py_file_count: int = 0
    total_file_count: int = 0
    files: list[FileEntry] = Field(default_factory=list)
    total_functions: int = 0
    avg_mi: float = 0
    high_complexity_functions: list[HighComplexityFunction] = Field(default_factory=list)
    unparseable_files: list[str] = Field(default_factory=list)
    dependency_nodes: list[DependencyNode] = Field(default_factory=list)
    dependency_edges: list[DependencyEdge] = Field(default_factory=list)
    cycles: list[DependencyCycle] = Field(default_factory=list)
    scc_count: int = 0
    most_depended_on: list[MostDependedOn] = Field(default_factory=list)
    most_unstable: list[MostUnstable] = Field(default_factory=list)
    smells: list[SmellModel] = Field(default_factory=list)
    smell_counts: dict[str, int] = Field(default_factory=dict)
    health_score: float = 100
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}
