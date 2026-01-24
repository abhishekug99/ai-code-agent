import os
from typing import Dict, List, Tuple

def build_module_map(scanned: List[Tuple[str, str]]) -> Dict[str, str]:
    """
    Maps repo-relative file paths to python module paths.
    e.g. "movieticketbooking/movie_booking_service.py" -> "movieticketbooking.movie_booking_service"
    Skips non-.py and __init__.py handled as package module.
    """
    module_map: Dict[str, str] = {}
    for rel_path, _ in scanned:
        p = rel_path.replace("\\", "/")
        if not p.endswith(".py"):
            continue
        mod = p[:-3].replace("/", ".")
        module_map[p] = mod
    return module_map

def detect_src_root(scanned_paths: List[str]) -> str:
    """
    Heuristic: if many files are under 'src/', suggest using src as root.
    Returns "" if none.
    """
    count_src = sum(1 for p in scanned_paths if p.replace("\\","/").startswith("src/"))
    return "src" if count_src >= 3 else ""
