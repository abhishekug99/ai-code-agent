from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

from agent.app.routers import edit, health

app = FastAPI(title="AI Code Agent")

app.include_router(health.router)
app.include_router(edit.router)


# @app.get("/health")
# def health_check():
#     return {"status": "ok",
#             "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}