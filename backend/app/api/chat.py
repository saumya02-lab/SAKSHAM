import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import (
    Conversation,
    Message,
    Citation,
    AuditLog,
    ToolCall,
    User,
)
from app.models.schemas import ChatRequest, RateRequest, AgentInfo
from app.orchestration.graph import run_orchestration
from app.memory.long_term import save_memories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Main chat endpoint — streams responses via SSE."""

    # Get or create conversation
    if req.conversation_id:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == req.conversation_id, Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title = req.message[:50] + ("..." if len(req.message) > 50 else "")
        conversation = Conversation(user_id=user_id, title=title)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    if req.regenerate:
        # The question is already stored. Remove the previous answer so we
        # replace it rather than appending a second reply to the same turn.
        prev = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.role == "assistant",
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_assistant = prev.scalar_one_or_none()
        if last_assistant:
            await db.delete(last_assistant)
            await db.commit()
    else:
        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=req.message,
        )
        db.add(user_msg)
        await db.commit()

        # Capture any durable facts/preferences stated in this message.
        await save_memories(req.message, user_id, db)

    # Resolve which agent to use. An explicit pick always wins; "auto" falls
    # back to the user's saved default_agent before the supervisor decides.
    requested_agent = req.agent
    if not requested_agent or requested_agent == "auto":
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        default_agent = (user.settings or {}).get("default_agent") if user else None
        if default_agent and default_agent != "auto":
            requested_agent = default_agent

    # Build conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history_messages = result.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content, "agent": m.agent}
        for m in history_messages
    ]

    async def event_generator():
        full_content = ""
        current_agent = None
        citations = []
        tool_calls_data = []

        try:
            async for event in run_orchestration(
                message=req.message,
                conversation_history=conversation_history,
                user_id=user_id,
                agent_override=requested_agent,
            ):
                event_type = event.get("type", "")

                if event_type == "routing":
                    yield {
                        "event": "routing",
                        "data": json.dumps(event["content"]),
                    }

                elif event_type == "agent":
                    current_agent = event["content"]
                    yield {
                        "event": "agent",
                        "data": json.dumps({"agent": current_agent}),
                    }

                elif event_type == "token":
                    token = event["content"]
                    full_content += token
                    yield {
                        "event": "token",
                        "data": json.dumps({"text": token}),
                    }

                elif event_type == "citation":
                    citations.append(event["data"])
                    yield {
                        "event": "citation",
                        "data": json.dumps(event["data"]),
                    }

                elif event_type == "tool":
                    tool_calls_data.append(event["content"])
                    yield {
                        "event": "tool",
                        "data": json.dumps({"tool": event["content"]}),
                    }

                elif event_type == "done":
                    if not full_content:
                        full_content = event.get("content", "")
                    if event.get("agent"):
                        current_agent = event["agent"]

        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_msg = f"I encountered an error: {str(e)}. Please try again."
            full_content = error_msg
            yield {
                "event": "token",
                "data": json.dumps({"text": error_msg}),
            }

        # Save assistant message
        from app.core.database import async_session
        async with async_session() as save_db:
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                agent=current_agent,
                content=full_content,
            )
            save_db.add(assistant_msg)
            await save_db.commit()
            await save_db.refresh(assistant_msg)

            # Save citations
            for cite in citations:
                citation = Citation(
                    message_id=assistant_msg.id,
                    source_title=cite.get("source_title"),
                    source_url=cite.get("source_url"),
                    snippet=cite.get("snippet"),
                )
                save_db.add(citation)

            # Save tool calls
            for tool_desc in tool_calls_data:
                tc = ToolCall(
                    message_id=assistant_msg.id,
                    tool=tool_desc,
                    input_data={"description": tool_desc},
                    output_data={},
                )
                save_db.add(tc)

            # Audit
            audit = AuditLog(
                user_id=user_id,
                action="chat",
                metadata_json={
                    "conversation_id": conversation.id,
                    "agent": current_agent,
                    "message_length": len(full_content),
                },
            )
            save_db.add(audit)

            # Update conversation timestamp
            conv_result = await save_db.execute(
                select(Conversation).where(Conversation.id == conversation.id)
            )
            conv = conv_result.scalar_one()
            conv.updated_at = datetime.now(timezone.utc)
            await save_db.commit()

            yield {
                "event": "done",
                "data": json.dumps({
                    "conversation_id": conversation.id,
                    "message_id": assistant_msg.id,
                }),
            }

    return EventSourceResponse(event_generator())


@router.post("/messages/{message_id}/rate", status_code=204)
async def rate_message(
    message_id: str,
    req: RateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Message.id == message_id, Conversation.user_id == user_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.rating = req.rating
    await db.commit()
    return None


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    return [
        AgentInfo(
            key="auto",
            name="Auto (Supervisor)",
            description="Automatically routes to the best agent",
        ),
        AgentInfo(
            key="research",
            name="Research Agent",
            description="Web search, document Q&A, summarization with citations",
        ),
        AgentInfo(
            key="coding",
            name="Coding Agent",
            description="Code generation, explanation, debugging, and tests",
        ),
        AgentInfo(
            key="email",
            name="Email/Writing Agent",
            description="Draft emails, adjust tone, summarize threads",
        ),
    ]


@router.post("/search")
async def search_docs(
    req: dict,
    user_id: str = Depends(get_current_user),
):
    from app.rag.retrieve import search_documents

    query = req.get("query", "")
    top_k = req.get("top_k", 5)

    if not query:
        raise HTTPException(status_code=422, detail="Query is required")

    results = await search_documents(query, user_id, top_k)
    return [
        {
            "chunk": r["chunk"],
            "score": r["score"],
            "source": r["source_name"],
        }
        for r in results
    ]
