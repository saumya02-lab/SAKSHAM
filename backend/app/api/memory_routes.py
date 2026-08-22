from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import Memory
from app.models.schemas import MemoryResponse, MemoryCreateRequest

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
    )
    memories = result.scalars().all()
    return [
        MemoryResponse(
            id=m.id,
            type=m.type,
            content=m.content,
            created_at=m.created_at,
        )
        for m in memories
    ]


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    req: MemoryCreateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mem = Memory(user_id=user_id, type=req.type, content=req.content)
    db.add(mem)
    await db.commit()
    await db.refresh(mem)
    return MemoryResponse(
        id=mem.id, type=mem.type, content=mem.content, created_at=mem.created_at
    )


@router.delete("", status_code=200)
async def clear_memories(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Forget everything stored about this user (US-17)."""
    result = await db.execute(delete(Memory).where(Memory.user_id == user_id))
    await db.commit()
    return {"deleted": result.rowcount or 0}


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
    )
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    await db.delete(mem)
    await db.commit()
    return None
