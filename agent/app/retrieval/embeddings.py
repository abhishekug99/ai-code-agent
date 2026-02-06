import os
from typing import List
from agent.app.llm.client import get_openai_client

def embed_texts(texts: List[str]) -> List[List[float]]:
    client = get_openai_client()
    model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding  for d in resp.data]

def embed_query(text: str)->List[float]:
    return embed_texts([text])[0]

