import os
from typing import List, Tuple, Set


DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "__pycache__",
    "node_modules", ".next", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}


def _is_within_repo(repo_root: str, abs_path: str) -> bool:
    repo_root = os.path.abspath(repo_root)
    abs_path = os.path.abspath(abs_path)
    try:
        return os.path.commonpath([repo_root, abs_path]) == repo_root
    except Exception:
        return False


def scan_repo_files(
    repo_root: str,
    scope_paths: List[str],
    max_files: int,
    max_bytes: int,
) -> List[Tuple[str, str]]:
    """
    Returns a list of (repo_relative_path, file_text) for scanned files.
    Bounded by max_files and max_bytes.
    """
    repo_root_abs = os.path.abspath(repo_root)
    results: List[Tuple[str, str]] = []
    total_bytes = 0

    def consider_file(abs_path: str) -> None:
        nonlocal total_bytes
        if len(results) >= max_files:
            return
        if not _is_within_repo(repo_root_abs, abs_path):
            return
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            return

        b = len(text.encode("utf-8", errors="ignore"))
        if total_bytes + b > max_bytes:
            return

        rel_path = os.path.relpath(abs_path, repo_root_abs).replace("\\", "/")
        results.append((rel_path, text))
        total_bytes += b

    for scope in scope_paths:
        scope_abs = os.path.abspath(os.path.join(repo_root_abs, scope))
        if not _is_within_repo(repo_root_abs, scope_abs):
            continue
        if os.path.isfile(scope_abs):
            consider_file(scope_abs)
            continue

        for root, dirs, files in os.walk(scope_abs):
            # prune ignored dirs in-place
            dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")]

            # stop early
            if len(results) >= max_files or total_bytes >= max_bytes:
                break

            for name in files:
                if len(results) >= max_files or total_bytes >= max_bytes:
                    break

                # Keep it simple: focus on python + key project metadata
                lower = name.lower()
                if not (lower.endswith(".py") or lower in {"pyproject.toml", "requirements.txt", "setup.cfg"}):
                    continue

                abs_path = os.path.join(root, name)
                consider_file(abs_path)

    return results
