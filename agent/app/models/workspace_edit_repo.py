from pydantic import BaseModel, Field
from typing import Optional, List


class WorkspaceEditRepoRequest(BaseModel):
    instruction: str = Field(..., min_length=1)

    # absolute path on disk (local machine)
    repo_root: str = Field(..., min_length=1)

    # directories inside repo_root to scan, e.g. ["src", "agent/app"]
    scope_paths: List[str] = Field(default_factory=lambda: ["."], min_length=1)

    # allowed roots (relative). model may only create/modify files under these dirs
    allowed_root_dirs: List[str] = Field(default_factory=lambda: ["tests"], min_length=1)

    # safety caps
    max_files: int = 200
    max_bytes: int = 800_000  # total bytes of scanned file contents

    # optional intent like "generate_tests"
    intent: Optional[str] = None

    user_context: Optional[str] = None
