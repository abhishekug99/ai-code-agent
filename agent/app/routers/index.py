from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import threading
import uuid
import time
import traceback

from agent.app.indexing.indexer import index_repo_to_quadrant
from agent.app.models.index import IndexStartRequest, IndexStartResponse, IndexStatusResponse

router = APIRouter()

# _JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS = {}

def _run_job(job_id: str, req: IndexStartRequest):
    _JOBS[job_id]["status"] = "running"
    try:
        res = index_repo_to_quadrant(
            repo_root=req.repo_root,
            scope_paths=req.scope_paths,
            max_files=req.max_files,
            max_bytes=req.max_bytes,
        )
        _JOBS[job_id]["status"] = "done"
        _JOBS[job_id]["finished_at"] = time.time()
        _JOBS[job_id]["result"] = res
    except Exception as e:
        _JOBS[job_id]["status"] = "error"
        _JOBS[job_id]["finished_at"] = time.time()
        _JOBS[job_id]["error"] = traceback.format_exc()
        
@router.post("/index/start", response_model=IndexStartResponse)
def index_start(req: IndexStartRequest):
    repo_root = os.path.abspath(req.repo_root)
    if not os.path.isdir(repo_root):
        raise HTTPException(status_code=400, detail=f"repo_root is not a directory: {repo_root}")
    
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "status": "queued",
        "started_at": time.time(),
        "finished_at": None,
        "result": None,
        "error": None,}
    
    print(type(_JOBS), type(_JOBS[job_id]))
    
    t = threading.Thread(target=_run_job, args=(job_id, req), daemon=True)
    t.start()
    
    return IndexStartResponse(job_id=job_id)

@router.get("/index/status/{job_id}", response_model=IndexStatusResponse)
def index_status(job_id: str):
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")

    return IndexStatusResponse(job_id=job_id, **job)



