from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.db_service import db_service
from app.services.llm_service import llm_service
from app.services.transcript_rag import transcript_rag
import asyncio
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Default partner names (fallback)
DEFAULT_PARTNER_A_NAME = "Adrian Malhotra"
DEFAULT_PARTNER_B_NAME = "Elara Voss"


def resolve_partner_names(partner_role: Optional[str]) -> tuple[str, str]:
    """Resolve partner and other name from partner_role. Returns (partner_name, other_name)."""
    if partner_role == "partner_b":
        return DEFAULT_PARTNER_B_NAME, DEFAULT_PARTNER_A_NAME
    # Default to partner_a
    return DEFAULT_PARTNER_A_NAME, DEFAULT_PARTNER_B_NAME


class ChatRequest(BaseModel):
    conflict_id: str
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = None
    partner_role: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    message_id: str
    sources: Optional[List[str]] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_luna(request: ChatRequest):
    try:
        partner_name, other_name = resolve_partner_names(request.partner_role)

        # 1. Fetch conflict + history in parallel with RAG lookup
        conflict_future = asyncio.to_thread(db_service.get_conflict, request.conflict_id)
        history_future = asyncio.to_thread(db_service.get_chat_history, request.conflict_id, 10)

        # Store user message (can run concurrently)
        store_future = asyncio.to_thread(
            db_service.store_chat_message,
            conflict_id=request.conflict_id,
            role="user",
            content=request.message
        )

        conflict = await conflict_future
        relationship_id = str(conflict["relationship_id"]) if conflict and conflict.get("relationship_id") else None

        # RAG lookup (needs relationship_id from conflict)
        rag_context, history, _ = await asyncio.gather(
            transcript_rag.rag_lookup(
                query=request.message,
                conflict_id=request.conflict_id,
                relationship_id=relationship_id
            ),
            history_future,
            store_future,
        )

        # Generate response
        luna_response = llm_service.generate_chat_response(
            user_message=request.message,
            rag_context=rag_context,
            conversation_history=history
        )

        # Store Luna's response
        message_id = db_service.store_chat_message(
            conflict_id=request.conflict_id,
            role="assistant",
            content=luna_response
        )

        return ChatResponse(
            response=luna_response,
            message_id=message_id,
            sources=[]
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_with_luna_stream(request: ChatRequest):
    """SSE streaming endpoint - returns tokens as they're generated"""
    try:
        partner_name, other_name = resolve_partner_names(request.partner_role)

        # 1. Fetch conflict + history in parallel
        conflict_future = asyncio.to_thread(db_service.get_conflict, request.conflict_id)
        history_future = asyncio.to_thread(db_service.get_chat_history, request.conflict_id, 10)
        store_future = asyncio.to_thread(
            db_service.store_chat_message,
            conflict_id=request.conflict_id,
            role="user",
            content=request.message
        )

        conflict = await conflict_future
        relationship_id = str(conflict["relationship_id"]) if conflict and conflict.get("relationship_id") else None

        rag_context, history, _ = await asyncio.gather(
            transcript_rag.rag_lookup(
                query=request.message,
                conflict_id=request.conflict_id,
                relationship_id=relationship_id
            ),
            history_future,
            store_future,
        )

        # Build messages for LLM with dynamic system prompt
        system_prompt = f"You are Luna, {partner_name}'s close friend and relationship mediator. You speak like a caring friend — empathetic but direct. Keep responses concise (2-4 sentences) unless the user asks for detail. Reference specific things from context when available. You're helping {partner_name} navigate their relationship with {other_name}."
        messages = [{"role": "system", "content": system_prompt}]
        if rag_context:
            messages.append({"role": "system", "content": f"Relevant Context:\n{rag_context}"})
        for msg in history:
            role = msg.get("role", "user")
            if role not in ["user", "assistant", "system"]:
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": request.message})

        async def event_stream():
            full_response = []
            try:
                for token in llm_service.chat_completion_stream(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800
                ):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

                # Store complete response
                complete_text = "".join(full_response)
                message_id = db_service.store_chat_message(
                    conflict_id=request.conflict_id,
                    role="assistant",
                    content=complete_text
                )
                yield f"data: {json.dumps({'done': True, 'message_id': message_id})}\n\n"
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
