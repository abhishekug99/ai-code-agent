from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class WorkspaceFileInput(BaseModel):
    file_path: str = Field(..., min_length=1)
    original_text: Optional[str] = None
    
class WorkspaceEditRequest(BaseModel):
    instruction: str = Field(..., min_length=1)
    files: List[WorkspaceFileInput] = Field(..., min_length=1)
    user_context: Optional[str] = None
    max_files: int = 10
    
class WorkspaceFileOutput(BaseModel):
    file_path: str
    action: Literal["create", "modify"]
    updated_text: str
    unified_diff: str = ""
    warnings: List[str] = []

class WorkspaceEditResponse(BaseModel):
    operations: List[WorkspaceFileOutput]
    warnings: List[str] = []
    

    