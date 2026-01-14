from pydantic import BaseModel, Field
from typing import List, Optional

class EditRequest(BaseModel):
    instruction: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    original_text: str = Field(..., min_length=1)
    user_context: Optional[str] = None
    
class EditResponse(BaseModel):
    file_path: str
    unified_diff: str
    updated_text: str
    warnings: List[str] = Field(default_factory=list)