import os
import hashlib
from typing import List, Tuple, Dict, Any
from agent.app.retrieval.repo_scan import scan_repo_files
from agent.app.retrieval.chunking import chunk_text_by_lines
from agent.app.retrieval.embeddings import embed_texts
from agent.app.retrieval.qdrant_store import ensure_collection, upsert_chunks

def _hash_text(s: str)->str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def index_repo_to_quadrant(
   repo_root: str,
    scope_paths: List[str],
    max_files: int,
    max_bytes: int,
    chunk_max_lines: int = 120,
    chunk_overlap: int = 20,
) -> Dict[str, Any]:
    scanned = scan_repo_files(repo_root, scope_paths, max_files, max_bytes)
    
    payloads = []
    texts = []
    
    for rel_path, text in scanned:
        if not rel_path.lower().endswith(".py"):
            continue
        for ch in chunk_text_by_lines(text, max_lines=chunk_max_lines, overlap=chunk_overlap):
            chunk_text = ch["text"]
            texts.append(chunk_text)
            payloads.append({
                "file_path": rel_path,
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "text": chunk_text,
                "content_hash": _hash_text(chunk_text),
            })
    if not texts:
        return {"indexed_chunks": 0, "indexed_files": 0}

    vectors = embed_texts(texts)
    dim = len(vectors[0])
    ensure_collection(dim)
    upsert_chunks(vectors, payloads)
    
    return {
        "indexed_chunks": len(payloads),
        "indexed_files": len({p["file_path"] for p in payloads}),
    }
        
    
    