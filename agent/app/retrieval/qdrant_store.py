import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)

def get_collection_name() -> str:
    return os.getenv("QDRANT_COLLECTION", "repo_chunks")

def ensure_collection(dim: int) -> None:
    client = get_qdrant_client()
    name = get_collection_name()
    existing = [c.name for c in client.get_collections().collections]
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
    )

def upsert_chunks(vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
    client = get_qdrant_client()
    name = get_collection_name()
    points = []
    for v, p in zip(vectors, payloads):
        points.append(qm.PointStruct(id=str(uuid.uuid4()), vector=v, payload=p))
    client.upsert(collection_name=name, points=points)

def search(query_vector: List[float], limit: int = 10, filter_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    client = get_qdrant_client()
    name = get_collection_name()

    qfilter = None
    if filter_paths:
        qfilter = qm.Filter(
            must=[qm.FieldCondition(key="file_path", match=qm.MatchAny(any=filter_paths))]
        )

    res = client.search(
        collection_name=name,
        query_vector=query_vector,
        limit=limit,
        query_filter=qfilter,
        with_payload=True,
    )
    out = []
    for r in res:
        p = r.payload or {}
        p["_score"] = float(r.score)
        out.append(p)
    return out
