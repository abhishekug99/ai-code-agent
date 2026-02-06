from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IndexStartRequest(BaseModel):
    repo_root: str = Field(..., min_length=1)
    scope_paths: List[str] = Field(default_factory=lambda:["."], min_length=1)
    max_files: int = 500
    max_bytes: int = 2_000_000

class IndexStartResponse(BaseModel):
    job_id: str
    
class IndexStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: float
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None