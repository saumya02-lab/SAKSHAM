import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.database import Document, AuditLog
from app.models.schemas import DocumentResponse, SearchRequest, SearchResultResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


@router.post("", response_model=DocumentResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, TXT, DOCX",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=422, detail="File too large (max 20MB)")

    file_id = str(uuid.uuid4())
    ext = ALLOWED_TYPES[file.content_type]
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=file_id,
        user_id=user_id,
        filename=file.filename,
        mime_type=file.content_type,
        status="ingesting",
        file_path=file_path,
    )
    db.add(doc)

    audit = AuditLog(
        user_id=user_id,
        action="upload_document",
        metadata_json={"document_id": file_id, "filename": file.filename},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(ingest_document, file_id, file_path, file.content_type, user_id)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        status=doc.status,
        created_at=doc.created_at,
    )


async def ingest_document(doc_id: str, file_path: str, mime_type: str, user_id: str):
    from app.rag.ingest import ingest_file
    from app.core.database import async_session

    async with async_session() as db:
        try:
            await ingest_file(doc_id, file_path, mime_type, user_id, db)
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one()
            doc.status = "ready"
            await db.commit()
        except Exception as e:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one()
            doc.status = "failed"
            await db.commit()
            print(f"Ingestion failed for {doc_id}: {e}")


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            mime_type=d.mime_type,
            status=d.status,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    from app.rag.ingest import delete_document_embeddings
    await delete_document_embeddings(document_id)

    await db.delete(doc)

    audit = AuditLog(
        user_id=user_id,
        action="delete_document",
        metadata_json={"document_id": document_id},
    )
    db.add(audit)
    await db.commit()
    return None
