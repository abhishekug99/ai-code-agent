import json
from typing import Optional, List, Dict, Any

SYSTEM_PROMPT_WORKSPACE = """You are an expert Python engineer.
You will receive an instruction and multiple files (some may be empty meaning new files).
You MUST return valid JSON only, matching the schema exactly.

Rules:
- Output ONLY JSON. No markdown. No prose.
- Only include files from the provided list.
- Keep changes minimal and safe.
- Do not invent extra files.
- Preserve style and imports unless required.
- If a file has original_text = null, you are creating it.
- Ensure Python code is syntactically correct where applicable.

JSON schema:
{
  "operations": [
    {
      "file_path": "relative/path.py",
      "updated_text": "full file content as string"
    }
  ]
}
"""

def build_user_prompt_workspace(
    instruction: str,
    files: List[Dict[str, Any]],
    user_context: Optional[str] = None
)->str:
    extra = f"\n\nAdditional context:\n{user_context}" if user_context else ""
    payload = {
        "instruction": instruction,
        "files": files
    }
    return f""" Here is the task and files in JSON:
    {json.dumps(payload, ensure_ascii=False)}
    {extra}
    """