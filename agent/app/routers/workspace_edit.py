from fastapi import APIRouter, HTTPException
import json
import os
from typing import Dict, Tuple

from agent.app.models.workspace_edit import (
    WorkspaceEditRequest,
    WorkspaceEditResponse,
    WorkspaceFileOutput
)

from agent.app.llm.client import get_openai_client
from agent.app.llm.workspace_prompts import SYSTEM_PROMPT_WORKSPACE, build_user_prompt_workspace
from agent.app.patch.diff import make_unified_diff

router  = APIRouter()

def _is_safe_repo_relative(path: str)-> bool:
    # block absolute paths + windows drive paths + parent traversal
    if os.path.isabs(path):
        return False
    
    if ":" in path.split("/")[0]: # block "C:\..." style when normalized badly
        return False
    
    normalized = path.replace("\\", "/")
    if normalized.startswith("../") or "/../" in normalized or normalized == "..":
        return False
    
    return True

def _index_originals(req: WorkspaceEditRequest)->Dict[str, str]:
    originals: Dict[str, str] = {}
    for f in req.files:
        originals[f.file_path] = f.original_text if f.original_text is not None else ""
    return originals

def _action_for_file(original_text: str)->str:
    return "create" if original_text == "" else "modify"

@router.post("/workspace_edit", response_model=WorkspaceEditResponse)
def workspace_edit(req: WorkspaceEditRequest):
    #safety: cap file count
    if len(req.files)> req.max_files:
        raise HTTPException(status_code=400, detail=f"Too many files. Max is {req.max_files}")
    
    seen = set()
    for f in req.files:
        if f.file_path in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate file_path: {f.file_path}")
        seen.add(f.file_path)
        
        if not _is_safe_repo_relative(f.file_path):
            raise HTTPException(status_code=400, detail=f"Unsafe file_path: {f.file_path}")
    originals_map = _index_originals(req)
    
    file_payload = [
        {"file_path": f.file_path, "originals_text": f.original_text}
        for f in req.files
    ]
    
    client = get_openai_client()
    user_prompt = build_user_prompt_workspace(req.instruction, file_payload, req.user_context)
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_WORKSPACE},
                    {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=500, detail="LLM returned empty response")
    
    #parse JSON strictly
    try:
        parsed = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM returned non-JSON output: {e}")         
    
    if not isinstance(parsed, dict) or "operations" not in parsed:
        raise HTTPException(status_code=500, detail="LLM JSON missing 'operations' field")
    
    ops = parsed.get("operations")
    if not isinstance(ops, list) or len(ops) == 0:
        raise HTTPException(status_code=500, detail="LLM JSON 'operations' must be a non-empty list")

    outputs = []
    top_warnings = []
    
    allowed_paths = set(originals_map.keys())
    
    for op in ops:
        if not isinstance(op, dict):
            top_warnings.append("Skipping invalid operation (not an object).")
            continue
        file_path = op.get("file_path")
        updated_text = op.get("updated_text")
        
        if not isinstance(file_path, str) or not isinstance(updated_text, str):
            top_warnings.append("Skipping invalid operation (missing file_path or updated_text).")
            continue
        
        if file_path not in allowed_paths:
            top_warnings.append(f"Model tried to edit non-allowed file: {file_path} (ignored).")
            continue
        
        original_text  = originals_map.get(file_path, "")
        action = _action_for_file(original_text)
        
        diff = ""
        warnings = []
        if action == "modify":
            diff = make_unified_diff(file_path, original_text, updated_text)
            if not diff.strip():
                warnings.append("No changes detected (diff is empty).")
        else:
            #create: diff optional, keep empty
            if updated_text.strip == "":
                warnings.append("Created file content is empty.")
        
        outputs.append(
            WorkspaceFileOutput(
                file_path=file_path,
                action=action, #type: ignore
                updated_text=updated_text,
                unified_diff=diff,
                warnings=warnings,
            )
        )
    if not outputs:
        raise HTTPException(status_code=500, detail="No valid operations returned by LLM")


    
    return WorkspaceEditResponse(operations=outputs, warnings=top_warnings)

            
    