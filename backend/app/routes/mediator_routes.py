from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.db_service import db_service
from app.services.llm_service import llm_service
from app.services.transcript_rag import transcript_rag
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    conflict_id: str
    message: str
    conversation_history: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    response: str
    message_id: str
    sources: Optional[List[str]] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_luna(request: ChatRequest):
    try:
        # 1. Fetch conflict details to get relationship_id
        conflict = db_service.get_conflict(request.conflict_id)
        relationship_id = str(conflict["relationship_id"]) if conflict and conflict.get("relationship_id") else None

        # 2. Store user message
        db_service.store_chat_message(
            conflict_id=request.conflict_id,
            role="user",
            content=request.message
        )
        
        # 3. Get relevant context via RAG
        rag_context = await transcript_rag.rag_lookup(
            query=request.message,
            conflict_id=request.conflict_id,
            relationship_id=relationship_id
        )
        
        # 4. Get conversation history from DB
        # We fetch the last 10 messages to provide context to the LLM
        history = db_service.get_chat_history(request.conflict_id, limit=10)
        
        # 5. Generate response
        luna_response = llm_service.generate_chat_response(
            user_message=request.message,
            rag_context=rag_context,
            conversation_history=history
        )
        
        # 6. Store Luna's response
        message_id = db_service.store_chat_message(
            conflict_id=request.conflict_id,
            role="assistant",
            content=luna_response
        )
        
        return ChatResponse(
            response=luna_response,
            message_id=message_id,
            sources=[] # Sources extraction can be added later if needed
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
