from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User
from app.models.schemas import SettingsUpdateRequest, UserResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserResponse)
async def get_settings(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        settings=user.settings or {},
        created_at=user.created_at,
    )


@router.patch("", response_model=UserResponse)
async def update_settings(
    req: SettingsUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.name is not None:
        user.name = req.name
    if req.settings is not None:
        user.settings = {**(user.settings or {}), **req.settings}

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        settings=user.settings or {},
        created_at=user.created_at,
    )
