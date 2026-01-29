import json
from typing import Any, Dict, List, Optional

SYSTEM_PROMPT_WORKSPACE_REPO = """You are an expert Python engineer.
You are given:
- an instruction
- a repo map and summaries of code (symbols, routes)
- selected file excerpts

You MUST return valid JSON only, matching the schema exactly.

Rules:
- Output ONLY JSON. No markdown. No prose.
- You may create/modify multiple files, but only under allowed_root_dirs.
- Prefer pytest if generating tests.
- Whenever creating new directory add __init__.py file.
- Keep changes minimal and consistent with repo conventions.
- Ensure Python code is syntactically correct.
- You may only create/modify files under allowed_root_dirs OR exactly listed in allowed_paths.

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

def build_user_prompt_workspace_repo(
    instruction: str,
    repo_map: Dict[str, Any],
    module_map: Dict[str, str],
    import_hint: Dict[str, Any],
    file_summaries: List[Dict[str, Any]],
    excerpts: List[Dict[str, Any]],
    allowed_root_dirs: List[str],
    allowed_paths: List[str],  
    intent: Optional[str] = None,
    user_context: Optional[str] = None,
) -> str:
    payload = {
        "instruction": instruction,
        "intent": intent,
        "allowed_root_dirs": allowed_root_dirs,
        "repo_map": repo_map,
        "import_hint": import_hint,
        "module_map": module_map,
        "file_summaries": file_summaries,
        "excerpts": excerpts,
        "user_context": user_context,
        "allowed_paths": allowed_paths,
    }
    return json.dumps(payload, ensure_ascii=False)
