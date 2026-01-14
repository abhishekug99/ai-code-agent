from fastapi import APIRouter, HTTPException
from agent.app.models.edit import EditRequest, EditResponse
from agent.app.llm.client import get_openai_client
from agent.app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from agent.app.patch.diff import make_unified_diff

router = APIRouter()

@router.post("/edit", response_model=EditResponse)
def edit(req: EditRequest):
    client = get_openai_client()

    prompt = build_user_prompt(
        file_path=req.file_path,
        instruction=req.instruction,
        original_text=req.original_text,
        user_context=req.user_context,
    )

    try:
        # You can swap model later; keep it simple for now.
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    updated_text = (resp.choices[0].message.content or "").strip("\n")

    if not updated_text:
        raise HTTPException(status_code=500, detail="LLM returned empty content")

    # Safety: if model accidentally returns same content, diff will be empty; still OK.
    diff = make_unified_diff(req.file_path, req.original_text, updated_text)

    warnings: list[str] = []
    if not diff.strip():
        warnings.append("No changes detected (diff is empty).")

    return EditResponse(
        file_path=req.file_path,
        unified_diff=diff,
        updated_text=updated_text,
        warnings=warnings,
    )
