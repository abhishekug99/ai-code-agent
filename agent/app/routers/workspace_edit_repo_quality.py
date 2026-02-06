from fastapi import APIRouter, HTTPException
import os, json, tempfile, shutil, subprocess
from typing import List, Dict, Any, Tuple, Optional

from agent.app.models.workspace_edit_repo import WorkspaceEditRepoRequest
from agent.app.models.workspace_edit import WorkspaceEditResponse, WorkspaceFileOutput
from agent.app.routers.workspace_edit_repo import workspace_edit_repo  # reuse logic
from agent.app.retrieval.repo_scan import DEFAULT_IGNORE_DIRS

router = APIRouter()

def _copy_repo(repo_root: str) -> str:
    ignore = shutil.ignore_patterns(*list(DEFAULT_IGNORE_DIRS))
    tmp = tempfile.mkdtemp(prefix="ai_agent_repo_")
    dst = os.path.join(tmp, "repo")
    shutil.copytree(repo_root, dst, ignore=ignore, dirs_exist_ok=True)
    return dst

def _apply_operations(repo_root: str, ops: List[WorkspaceFileOutput]) -> None:
    for op in ops:
        rel = op.file_path.replace("\\", "/").lstrip("/")
        abs_path = os.path.join(repo_root, rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(op.updated_text)

def _run_pytest(repo_root: str, timeout_s: int = 120) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            ["pytest", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return p.returncode, out.strip()
    except Exception as e:
        return 2, f"pytest execution failed: {e}"

@router.post("/workspace_edit_repo_quality", response_model=WorkspaceEditResponse)
def workspace_edit_repo_quality(req: WorkspaceEditRepoRequest):
    # attempt 1
    resp1: WorkspaceEditResponse = workspace_edit_repo(req)  # type: ignore

    tmp_repo = _copy_repo(os.path.abspath(req.repo_root))
    _apply_operations(tmp_repo, resp1.operations)

    code, out = _run_pytest(tmp_repo)
    if code == 0:
        # attach pytest summary as warning for visibility
        resp1.warnings.append("pytest passed in quality loop")
        return resp1

    # attempt 2 with failure context
    req2 = WorkspaceEditRepoRequest(
        instruction=req.instruction,
        repo_root=req.repo_root,
        scope_paths=req.scope_paths,
        allowed_root_dirs=req.allowed_root_dirs,
        max_files=req.max_files,
        max_bytes=req.max_bytes,
        intent=req.intent,
        user_context=(req.user_context or "") + "\n\nPytest failed output:\n" + out
    )
    resp2: WorkspaceEditResponse = workspace_edit_repo(req2)  # type: ignore

    tmp_repo2 = _copy_repo(os.path.abspath(req.repo_root))
    _apply_operations(tmp_repo2, resp2.operations)
    code2, out2 = _run_pytest(tmp_repo2)

    if code2 == 0:
        resp2.warnings.append("pytest passed after 1 retry in quality loop")
        return resp2

    resp2.warnings.append("pytest still failing after retry")
    resp2.warnings.append(out2[:4000])
    return resp2
