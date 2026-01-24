from fastapi import APIRouter, HTTPException
import json
import os
from typing import List, Dict, Any, Tuple

from agent.app.models.workspace_edit_repo import WorkspaceEditRepoRequest
from agent.app.models.workspace_edit import WorkspaceEditResponse, WorkspaceFileOutput
from agent.app.llm.client import get_openai_client
from agent.app.llm.workspace_repo_prompts import SYSTEM_PROMPT_WORKSPACE_REPO, build_user_prompt_workspace_repo
from agent.app.patch.diff import make_unified_diff
from agent.app.retrieval.repo_scan import scan_repo_files
from agent.app.retrieval.py_symbols import extract_python_summary
from agent.app.retrieval.module_map import build_module_map, detect_src_root


router = APIRouter()


def _is_safe_repo_relative(path: str) -> bool:
    if os.path.isabs(path):
        return False
    if ":" in path.split("/")[0]:
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith("../") or "/../" in normalized or normalized == "..":
        return False
    return True


def _is_under_allowed_roots(rel_path: str, allowed_roots: List[str]) -> bool:
    rel = rel_path.replace("\\", "/").lstrip("/")
    for root in allowed_roots:
        r = root.replace("\\", "/").strip("/")
        if r == "":
            continue
        if rel == r or rel.startswith(r + "/"):
            return True
    return False


def _score_file(rel_path: str) -> int:
    p = rel_path.lower()
    score = 0
    # prefer "real code" over tests for context
    if "/tests/" in p or p.startswith("tests/") or p.endswith("_test.py") or p.startswith("test_"):
        score -= 2
    # likely important
    for kw, w in [
        ("main.py", 5),
        ("app.py", 4),
        ("router", 4),
        ("routes", 4),
        ("service", 3),
        ("controller", 3),
        ("model", 3),
        ("schema", 3),
        ("db", 2),
        ("crud", 2),
        ("utils", 1),
        ("config", 1),
    ]:
        if kw in p:
            score += w
    # python files are main signal
    if p.endswith(".py"):
        score += 1
    return score


def _build_repo_map(files: List[Tuple[str, str]]) -> Dict[str, Any]:
    rel_paths = [rp for rp, _ in files]
    top_dirs = {}
    for rp in rel_paths:
        parts = rp.split("/")
        if len(parts) >= 2:
            top_dirs[parts[0]] = top_dirs.get(parts[0], 0) + 1
        else:
            top_dirs["."] = top_dirs.get(".", 0) + 1
    return {
        "file_count_scanned": len(files),
        "top_level_dirs": sorted(top_dirs.items(), key=lambda x: x[1], reverse=True)[:25],
        "sample_paths": rel_paths[:50],
    }


@router.post("/workspace_edit_repo", response_model=WorkspaceEditResponse)
def workspace_edit_repo(req: WorkspaceEditRepoRequest):
    repo_root = os.path.abspath(req.repo_root)
    if not os.path.isdir(repo_root):
        raise HTTPException(status_code=400, detail=f"repo_root is not a directory: {repo_root}")

    # Scan files (bounded)
    scanned = scan_repo_files(
        repo_root=repo_root,
        scope_paths=req.scope_paths,
        max_files=req.max_files,
        max_bytes=req.max_bytes,
    )
    if not scanned:
        raise HTTPException(status_code=400, detail="No files scanned. Check scope_paths and repo_root.")
    
    scanned_paths = [rp for rp, _ in scanned]
    module_map = build_module_map(scanned)
    src_root = detect_src_root(scanned_paths)

    import_hint = {
        "src_root_detected": src_root,
        "note": "Use module_map to form correct imports. If src_root_detected is 'src', imports likely start from package under src/.",
        }


    # Build summaries
    summaries: List[Dict[str, Any]] = []
    for rel_path, text in scanned:
        if rel_path.lower().endswith(".py"):
            s = extract_python_summary(text)
            s["file_path"] = rel_path
            summaries.append(s)

    # Select excerpts for LLM: top scored + small cap
    scored = sorted(scanned, key=lambda x: _score_file(x[0]), reverse=True)
    excerpt_cap = 18  # keep prompt bounded
    excerpts: List[Dict[str, Any]] = []
    for rel_path, text in scored[:excerpt_cap]:
        # truncate excerpt to reduce prompt size
        snippet = text[:4000]
        excerpts.append({"file_path": rel_path, "excerpt": snippet})

    repo_map = _build_repo_map(scanned)

    client = get_openai_client()
    user_prompt = build_user_prompt_workspace_repo(
        instruction=req.instruction,
        repo_map=repo_map,
        module_map=module_map,
        import_hint=import_hint,
        file_summaries=summaries[:80],  # cap
        excerpts=excerpts,
        allowed_root_dirs=req.allowed_root_dirs,
        intent=req.intent,
        user_context=req.user_context,
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_WORKSPACE_REPO},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=500, detail="LLM returned empty response")

    # Parse JSON
    try:
        parsed = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM returned non-JSON output: {e}")

    ops = parsed.get("operations")
    if not isinstance(ops, list) or len(ops) == 0:
        raise HTTPException(status_code=500, detail="LLM JSON 'operations' must be a non-empty list")

    # Build originals map from scanned files for diffs (only if the file exists)
    originals_map: Dict[str, str] = {rp: txt for rp, txt in scanned}

    outputs: List[WorkspaceFileOutput] = []
    top_warnings: List[str] = []

    for op in ops:
        if not isinstance(op, dict):
            top_warnings.append("Skipping invalid operation (not an object).")
            continue

        file_path = op.get("file_path")
        updated_text = op.get("updated_text")

        if not isinstance(file_path, str) or not isinstance(updated_text, str):
            top_warnings.append("Skipping invalid operation (missing file_path or updated_text).")
            continue

        if not _is_safe_repo_relative(file_path):
            top_warnings.append(f"Unsafe file_path returned by model (ignored): {file_path}")
            continue

        if not _is_under_allowed_roots(file_path, req.allowed_root_dirs):
            top_warnings.append(f"File not under allowed_root_dirs (ignored): {file_path}")
            continue

        original_text = originals_map.get(file_path)
        action = "modify" if original_text is not None else "create"

        diff = ""
        warnings: List[str] = []

        if action == "modify":
            diff = make_unified_diff(file_path, original_text, updated_text)
            if not diff.strip():
                warnings.append("No changes detected (diff is empty).")
        else:
            if updated_text.strip() == "":
                warnings.append("Created file content is empty.")

        outputs.append(
            WorkspaceFileOutput(
                file_path=file_path,
                action=action,  # type: ignore
                updated_text=updated_text,
                unified_diff=diff,
                warnings=warnings,
            )
        )

    if not outputs:
        raise HTTPException(
            status_code=400,
            detail=f"No valid operations returned. Warnings: {top_warnings}"
        )

    return WorkspaceEditResponse(operations=outputs, warnings=top_warnings)
