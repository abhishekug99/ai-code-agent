from typing import List, Dict, Any

def chunk_text_by_lines(text: str, max_lines: int = 120, overlap: int = 20)->List[Dict[str, Any]]:
    lines = text.splitlines()
    chunks = []
    i = 0
    n = len(lines)
    while i<n:
        start = i
        end = min(n, i+max_lines)
        chunk_lines  = lines[start:end]
        chunk_text = "\n".join(chunk_lines)
        chunks.append({
            "start_line": start + 1,
            "end_line": end,
            "text": chunk_text
        })
        if end == n:
            break
        i = max(end - overlap, end) if overlap<=0 else end - overlap
    return chunks
    