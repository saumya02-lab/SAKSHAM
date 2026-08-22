from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Auth ──
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    settings: dict = {}
    created_at: datetime


# ── Chat ──
class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    agent: Optional[str] = "auto"
    # True when re-answering the last question: the user message is already
    # stored, so it must not be saved again (FR-18 regenerate).
    regenerate: bool = False


class MessageResponse(BaseModel):
    id: str
    role: str
    agent: Optional[str] = None
    content: str
    rating: Optional[str] = None
    citations: List["CitationResponse"] = []
    created_at: datetime


class CitationResponse(BaseModel):
    id: str
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    snippet: Optional[str] = None


class RateRequest(BaseModel):
    rating: str  # "up" or "down"


# ── Conversations ──
class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime


# ── Documents ──
class DocumentResponse(BaseModel):
    id: str
    filename: str
    mime_type: Optional[str] = None
    status: str
    created_at: datetime


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResultResponse(BaseModel):
    chunk: str
    score: float
    source: str


# ── Memory ──
class MemoryResponse(BaseModel):
    id: str
    type: str
    content: str
    created_at: datetime


class MemoryCreateRequest(BaseModel):
    type: str = "fact"
    content: str


# ── Settings ──
class SettingsUpdateRequest(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


# ── Audit ──
class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    metadata_json: dict = {}
    created_at: datetime


# ── Agents ──
class AgentInfo(BaseModel):
    key: str
    name: str
    description: str
