from fastapi import APIRouter
import os

router  = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok", "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}
