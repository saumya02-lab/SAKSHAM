import asyncio
import logging
from typing import List, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_chroma_client():
    import chromadb

    client = chromadb.HttpClient(
        host=settings.CHROMA_URL.replace("http://", "").split(":")[0],
        port=int(settings.CHROMA_URL.split(":")[-1]),
    )
    return client


def _query_sync(query: str, user_id: str, top_k: int) -> List[Dict]:
    """Blocking ChromaDB query. Must be run in a worker thread."""
    client = get_chroma_client()
    collection_name = f"user_{user_id}"

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    results = collection.query(query_texts=[query], n_results=top_k)

    if not results or not results.get("documents"):
        return []

    chunks = []
    docs = results["documents"][0]
    metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
    distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

    for doc, meta, dist in zip(docs, metadatas, distances):
        chunks.append({
            "content": doc,
            "document_id": meta.get("document_id", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "score": 1.0 - dist,  # Convert distance to similarity
        })

    return chunks


async def retrieve_relevant_chunks(
    query: str,
    user_id: str,
    top_k: int = 5,
) -> List[Dict]:
    """Retrieve the most relevant chunks from a user's document collection.

    The chromadb client is synchronous, so it runs on a worker thread to
    avoid blocking the event loop during a streaming chat response.
    """
    try:
        return await asyncio.to_thread(_query_sync, query, user_id, top_k)
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return []


async def search_documents(
    query: str,
    user_id: str,
    top_k: int = 5,
) -> List[Dict]:
    """Search user documents and return results with source info."""
    from sqlalchemy import select
    from app.core.database import async_session
    from app.models.database import Document

    chunks = await retrieve_relevant_chunks(query, user_id, top_k)

    if not chunks:
        return []

    doc_ids = list(set(c["document_id"] for c in chunks))

    async with async_session() as db:
        result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        docs = {d.id: d for d in result.scalars().all()}

    return [
        {
            "chunk": c["content"],
            "score": c["score"],
            "source_name": docs[c["document_id"]].filename if c["document_id"] in docs else "Unknown",
            "document_id": c["document_id"],
        }
        for c in chunks
    ]
