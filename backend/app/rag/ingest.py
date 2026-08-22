import asyncio
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import DocChunk

logger = logging.getLogger(__name__)


def extract_text(file_path: str, mime_type: str) -> str:
    """Extract text from a file based on its MIME type."""
    if mime_type == "text/plain":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif mime_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def get_chroma_client():
    """Get or create a ChromaDB client."""
    import chromadb

    client = chromadb.HttpClient(host=settings.CHROMA_URL.replace("http://", "").split(":")[0],
                                  port=int(settings.CHROMA_URL.split(":")[-1]))
    return client


def _add_to_chroma(doc_id: str, chunks: List[str], user_id: str, batch_size: int = 100):
    """Blocking ChromaDB write. Must be run in a worker thread."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=f"user_{user_id}",
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.add(
            documents=batch,
            ids=[f"{doc_id}_chunk_{start + i}" for i in range(len(batch))],
            metadatas=[
                {
                    "document_id": doc_id,
                    "chunk_index": start + i,
                    "user_id": user_id,
                }
                for i in range(len(batch))
            ],
        )


async def ingest_file(
    doc_id: str,
    file_path: str,
    mime_type: str,
    user_id: str,
    db: AsyncSession,
):
    """Ingest a document: extract text, chunk, embed, and store."""
    logger.info(f"Ingesting document {doc_id}")

    text = await asyncio.to_thread(extract_text, file_path, mime_type)
    if not text.strip():
        raise ValueError("No text extracted from document")

    chunks = chunk_text(text)
    logger.info(f"Created {len(chunks)} chunks for document {doc_id}")

    try:
        await asyncio.to_thread(_add_to_chroma, doc_id, chunks, user_id)
    except Exception as e:
        logger.warning(f"ChromaDB ingestion failed (will continue without vector search): {e}")

    for i, chunk in enumerate(chunks):
        doc_chunk = DocChunk(
            document_id=doc_id,
            chunk_index=i,
            content=chunk,
            embedding_id=f"{doc_id}_chunk_{i}",
        )
        db.add(doc_chunk)

    await db.commit()
    logger.info(f"Ingestion complete for document {doc_id}")


async def delete_document_embeddings(doc_id: str):
    """Delete document embeddings from ChromaDB."""
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        for col in collections:
            try:
                collection = client.get_collection(col.name)
                results = collection.get(where={"document_id": doc_id})
                if results and results["ids"]:
                    collection.delete(ids=results["ids"])
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Failed to delete embeddings: {e}")
