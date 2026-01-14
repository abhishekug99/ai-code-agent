from difflib import unified_diff

def make_unified_diff(file_path: str, original_text: str, updated_text: str)-> str:
    original_lines = original_text.splitlines(keepends=True)
    updated_lines = updated_text.splitlines(keepends=True)
    
    diff_lines = unified_diff(
        original_lines,
        updated_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="\n",
    )
    
    return "".join(diff_lines)
