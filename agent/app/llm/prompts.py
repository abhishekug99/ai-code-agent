from typing import Optional

SYSTEM_PROMPT = """You are an expert Python engineer.
You will be given a file's content and an instruction.
Return ONLY the updated file content. Do not wrap in Markdown. Do not add explanations.
Keep changes minimal and localized to satisfy the instruction.
Preserve existing style, imports, and formatting unless needed."""

def build_user_prompt(file_path: str, instruction: str, original_text: str, user_context: Optional[str] = None)->str:
    extra = f"\n\nAdditional context:\n{user_context}" if user_context else ""
    return f"""File Path: {file_path}

Instruction: {instruction}{extra}
Original File Content:
{original_text}"""
