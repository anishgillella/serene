"""
VAPI Webhook handlers for Luna voice assistant.

This module handles:
- Dynamic assistant configuration
- Tool execution (find_similar_conflicts, get_partner_perspective)
- Message logging
- Session management
"""

import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.services.db_service import db_service
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.s3_service import s3_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vapi", tags=["vapi"])


# ============================================
# PYDANTIC MODELS
# ============================================

class ToolCallRequest(BaseModel):
    """Request model for tool calls from VAPI"""
    message: Dict[str, Any]


class VAPIWebhookRequest(BaseModel):
    """Generic VAPI webhook request"""
    message: Dict[str, Any]


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_luna_system_prompt(
    partner_a_name: str,
    partner_b_name: str,
    conflict_context: Optional[str] = None
) -> str:
    """Generate Luna's system prompt with partner names and conflict context."""

    context_section = ""
    if conflict_context:
        context_section = f"""

## Current Conflict Context:
{conflict_context}

Use this context to have a more informed conversation. Reference specific things they said or issues that came up naturally.
"""

    return f"""You are Luna, {partner_a_name}'s buddy who helps them think through relationship stuff with {partner_b_name}.

## Your Personality:
- Warm, casual, and real - like a close friend they trust
- Keep responses SHORT (2-3 sentences max for voice)
- Use natural phrases: "I hear you", "That's tough", "I get it"
- Validate their feelings without being repetitive
- Be honest - gently call out behavior when needed
- Help them see {partner_b_name}'s perspective without making them feel wrong

## Your Approach:
1. Listen and let them vent first
2. Validate their feelings naturally (vary your language)
3. Help them understand {partner_b_name}'s side
4. Suggest practical, real-world fixes
5. Be supportive but also help them grow

## Important Rules:
- NEVER use clinical therapy language
- Keep responses conversational and brief (this is voice, not text)
- Don't overuse filler words like "man", "bro", "dude"
- When they share something hard, acknowledge it simply: "That's really tough" or "I get why that hurt"
- Be willing to push back gently: "I hear you, but have you thought about how {partner_b_name} might see this?"
{context_section}
## Context Awareness:
When you have context about their relationship patterns, reference it naturally:
- "You mentioned this came up before..."
- "Based on what you've shared about {partner_b_name}..."
"""


async def get_conflict_context(conflict_id: str) -> Optional[str]:
    """Fetch conflict context including transcript and analysis."""
    try:
        context_parts = []

        # Get conflict with transcript
        conflict_data = db_service.get_conflict_with_transcript(conflict_id)
        if conflict_data and conflict_data.get("transcript_text"):
            transcript = conflict_data["transcript_text"]
            # Truncate if too long (keep it manageable for the LLM)
            if len(transcript) > 2000:
                transcript = transcript[:2000] + "..."
            context_parts.append(f"### Recent Conversation:\n{transcript}")

        # Get conflict analysis from S3 if available
        analysis_meta = db_service.get_conflict_analysis(conflict_id)
        if analysis_meta and analysis_meta.get("analysis_path"):
            # Strip s3://bucket-name/ prefix if present
            analysis_path = analysis_meta["analysis_path"]
            if analysis_path.startswith("s3://"):
                # Extract just the key part (after bucket name)
                parts = analysis_path.replace("s3://", "").split("/", 1)
                if len(parts) > 1:
                    analysis_path = parts[1]
            analysis_bytes = s3_service.download_file(analysis_path)
            if analysis_bytes:
                analysis = json.loads(analysis_bytes.decode('utf-8'))

                # Extract key insights
                if analysis.get("fight_summary"):
                    context_parts.append(f"### Summary:\n{analysis['fight_summary']}")

                if analysis.get("root_causes"):
                    causes = ", ".join(analysis["root_causes"][:3])
                    context_parts.append(f"### Root Causes:\n{causes}")

                if analysis.get("unmet_needs_partner_a"):
                    needs_a = ", ".join(analysis["unmet_needs_partner_a"][:3])
                    context_parts.append(f"### Partner A's Unmet Needs:\n{needs_a}")

                if analysis.get("unmet_needs_partner_b"):
                    needs_b = ", ".join(analysis["unmet_needs_partner_b"][:3])
                    context_parts.append(f"### Partner B's Unmet Needs:\n{needs_b}")

        if context_parts:
            return "\n\n".join(context_parts)

        return None

    except Exception as e:
        logger.error(f"Error fetching conflict context: {e}")
        return None


async def find_similar_conflicts_impl(
    topic_keywords: str,
    relationship_id: str,
    conflict_id: str
) -> str:
    """Find similar past conflicts using vector search."""
    try:
        # Generate embedding for the query
        query_embedding = await embeddings_service.get_embedding(topic_keywords)

        # Search in conflict_summaries namespace
        results = pinecone_service.query(
            vector=query_embedding,
            top_k=5,
            namespace="conflict_summaries",
            filter={
                "relationship_id": relationship_id,
                "conflict_id": {"$ne": conflict_id}  # Exclude current conflict
            },
            include_metadata=True
        )

        if not results.matches:
            return "I don't see any similar past conflicts in your history. This might be a new pattern for you two."

        # Format results
        summaries = []
        seen_conflicts = set()

        for match in results.matches:
            c_id = match.metadata.get("conflict_id", "")
            if c_id in seen_conflicts:
                continue
            seen_conflicts.add(c_id)

            topic = match.metadata.get("topic", "Unknown topic")
            date = match.metadata.get("date", "")
            status = match.metadata.get("status", "unresolved")

            summaries.append(f"- {topic} ({date}, {status})")

            if len(summaries) >= 3:
                break

        if not summaries:
            return "I couldn't find any similar past conflicts."

        return f"Here are some similar past conflicts:\n" + "\n".join(summaries)

    except Exception as e:
        logger.error(f"Error finding similar conflicts: {e}")
        return "I couldn't search your past conflicts right now."


async def get_partner_perspective_impl(
    situation_description: str,
    relationship_id: str,
    partner_b_name: str
) -> str:
    """Get partner's perspective based on their profile."""
    try:
        # Fetch partner B's profile from Pinecone
        query_embedding = await embeddings_service.get_embedding(
            f"partner profile personality {partner_b_name}"
        )

        results = pinecone_service.query(
            vector=query_embedding,
            top_k=3,
            namespace="profiles",
            filter={"relationship_id": relationship_id, "partner": "partner_b"},
            include_metadata=True
        )

        profile_context = ""
        if results.matches:
            for match in results.matches:
                profile_context += match.metadata.get("text", "") + "\n"

        if not profile_context:
            return f"Based on what you've shared, {partner_b_name} might be feeling unheard or misunderstood in this situation."

        # Use LLM to generate perspective
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )

        response = await client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are helping someone understand their partner's perspective.

Partner Profile:
{profile_context}

Based on this profile, explain in 2-3 sentences how {partner_b_name} might be feeling or thinking about the situation described. Use they/them pronouns. Be empathetic but honest."""
                },
                {
                    "role": "user",
                    "content": f"Situation: {situation_description}"
                }
            ],
            max_tokens=150,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error getting partner perspective: {e}")
        return f"I think {partner_b_name} might have a different take on this. What do you think they'd say?"


# ============================================
# WEBHOOK ENDPOINTS
# ============================================

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Main VAPI webhook endpoint.
    Handles all event types from VAPI.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        event_type = message.get("type", "")

        logger.info(f"📞 VAPI webhook received: {event_type}")

        # Handle different event types
        if event_type == "assistant-request":
            # Dynamic assistant configuration
            return await handle_assistant_request(message)

        elif event_type == "function-call":
            # Tool execution
            return await handle_function_call(message)

        elif event_type == "transcript":
            # Log transcript
            return await handle_transcript(message)

        elif event_type == "end-of-call-report":
            # Session ended
            return await handle_end_of_call(message)

        elif event_type == "status-update":
            # Call status changed
            status = message.get("status", "")
            logger.info(f"📞 Call status: {status}")
            return {"status": "ok"}

        else:
            logger.debug(f"Unhandled event type: {event_type}")
            return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ VAPI webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_assistant_request(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle assistant-request event.
    Returns dynamic assistant configuration with context.
    """
    try:
        call = message.get("call", {})
        metadata = call.get("metadata", {})

        conflict_id = metadata.get("conflict_id", "")
        relationship_id = metadata.get("relationship_id", "")
        partner_a_name = metadata.get("partner_a_name", "Adrian")
        partner_b_name = metadata.get("partner_b_name", "Elara")

        logger.info(f"🎯 Assistant request for conflict: {conflict_id}")
        logger.info(f"👥 Partners: {partner_a_name} & {partner_b_name}")

        # Create DB session for logging
        session_id = None
        if conflict_id:
            session_id = db_service.create_mediator_session(conflict_id)
            logger.info(f"✅ Created session: {session_id}")

        # Fetch conflict context (transcript, analysis, etc.)
        conflict_context = None
        if conflict_id:
            conflict_context = await get_conflict_context(conflict_id)
            if conflict_context:
                logger.info(f"📋 Loaded conflict context ({len(conflict_context)} chars)")
            else:
                logger.info("⚠️ No conflict context available")

        # Generate dynamic system prompt with context
        system_prompt = get_luna_system_prompt(
            partner_a_name,
            partner_b_name,
            conflict_context
        )

        # Return assistant configuration
        return {
            "assistant": {
                "firstMessage": f"Hey {partner_a_name}! I'm Luna. What's on your mind?",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "maxTokens": 250,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        }
                    ]
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                    "model": "eleven_flash_v2_5"
                },
                "metadata": {
                    **metadata,
                    "session_id": session_id
                }
            }
        }

    except Exception as e:
        logger.error(f"Error handling assistant request: {e}")
        return {"error": str(e)}


async def handle_function_call(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle function-call event.
    Executes the requested tool and returns result.
    """
    try:
        function_call = message.get("functionCall", {})
        function_name = function_call.get("name", "")
        parameters = function_call.get("parameters", {})

        call = message.get("call", {})
        metadata = call.get("metadata", {})

        conflict_id = metadata.get("conflict_id", "")
        relationship_id = metadata.get("relationship_id", "")
        partner_b_name = metadata.get("partner_b_name", "Partner B")

        logger.info(f"🔧 Tool call: {function_name}")

        result = ""

        if function_name == "find_similar_conflicts":
            topic_keywords = parameters.get("topic_keywords", "")
            result = await find_similar_conflicts_impl(
                topic_keywords=topic_keywords,
                relationship_id=relationship_id,
                conflict_id=conflict_id
            )

        elif function_name == "get_partner_perspective":
            situation_description = parameters.get("situation_description", "")
            result = await get_partner_perspective_impl(
                situation_description=situation_description,
                relationship_id=relationship_id,
                partner_b_name=partner_b_name
            )

        else:
            result = f"Unknown tool: {function_name}"
            logger.warning(f"Unknown tool called: {function_name}")

        return {"result": result}

    except Exception as e:
        logger.error(f"Error executing function: {e}")
        return {"result": f"Sorry, I couldn't complete that request: {str(e)}"}


async def handle_transcript(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle transcript event.
    Logs messages to database.
    """
    try:
        call = message.get("call", {})
        metadata = call.get("metadata", {})
        session_id = metadata.get("session_id")

        transcript = message.get("transcript", "")
        role = message.get("role", "user")

        if session_id and transcript:
            db_service.save_mediator_message(
                session_id=session_id,
                role=role,
                content=transcript
            )
            logger.debug(f"💬 Logged {role} message")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error logging transcript: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/context/{conflict_id}")
async def get_voice_context(conflict_id: str):
    """
    Get context for a voice call.
    Frontend calls this before starting VAPI call to get dynamic system prompt.
    """
    try:
        logger.info(f"📋 Fetching voice context for conflict: {conflict_id}")

        # Fetch conflict context
        conflict_context = await get_conflict_context(conflict_id)

        # Generate system prompt with context
        system_prompt = get_luna_system_prompt(
            partner_a_name="Adrian",
            partner_b_name="Elara",
            conflict_context=conflict_context
        )

        # Generate a context-aware first message
        first_message = "Hey Adrian! I'm Luna. What's on your mind?"
        if conflict_context:
            # Try to get a summary from the analysis
            analysis_meta = db_service.get_conflict_analysis(conflict_id)
            if analysis_meta and analysis_meta.get("analysis_path"):
                # Strip s3://bucket-name/ prefix if present
                analysis_path = analysis_meta["analysis_path"]
                if analysis_path.startswith("s3://"):
                    parts = analysis_path.replace("s3://", "").split("/", 1)
                    if len(parts) > 1:
                        analysis_path = parts[1]
                analysis_bytes = s3_service.download_file(analysis_path)
                if analysis_bytes:
                    analysis = json.loads(analysis_bytes.decode('utf-8'))
                    summary = analysis.get("fight_summary", "")
                    if summary:
                        # Truncate and create a personalized opener
                        short_summary = summary[:150] + "..." if len(summary) > 150 else summary
                        first_message = f"Hey Adrian! I'm Luna. I read through what happened - {short_summary} How are you feeling about it now?"
                    else:
                        first_message = "Hey Adrian! I'm Luna. I saw the conversation between you and Elara. It sounds like things got a bit tense. Want to talk through what happened?"
            else:
                first_message = "Hey Adrian! I'm Luna. I saw the conversation between you and Elara. It sounds like things got a bit tense. Want to talk through what happened?"

        return {
            "success": True,
            "system_prompt": system_prompt,
            "first_message": first_message,
            "has_context": conflict_context is not None,
            "context_preview": conflict_context[:200] + "..." if conflict_context and len(conflict_context) > 200 else conflict_context
        }

    except Exception as e:
        logger.error(f"Error fetching voice context: {e}")
        return {
            "success": False,
            "system_prompt": get_luna_system_prompt("Adrian", "Elara"),
            "first_message": "Hey Adrian! I'm Luna. What's on your mind?",
            "has_context": False,
            "error": str(e)
        }


async def handle_end_of_call(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle end-of-call-report event.
    Saves session summary and cleanup.
    """
    try:
        call = message.get("call", {})
        metadata = call.get("metadata", {})
        session_id = metadata.get("session_id")

        summary = message.get("summary", "")
        duration = message.get("durationSeconds", 0)

        logger.info(f"📞 Call ended. Duration: {duration}s, Session: {session_id}")

        # Could save summary to DB here if needed

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error handling end of call: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# DIRECT TOOL ENDPOINTS (Alternative to webhook)
# ============================================

@router.post("/tools/find_similar_conflicts")
async def tool_find_similar_conflicts(request: Request):
    """Direct endpoint for find_similar_conflicts tool."""
    try:
        body = await request.json()
        message = body.get("message", {})

        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})

        call = message.get("call", {})
        metadata = call.get("metadata", {})

        result = await find_similar_conflicts_impl(
            topic_keywords=parameters.get("topic_keywords", ""),
            relationship_id=metadata.get("relationship_id", ""),
            conflict_id=metadata.get("conflict_id", "")
        )

        return {"result": result}

    except Exception as e:
        logger.error(f"Error in find_similar_conflicts: {e}")
        return {"result": "I couldn't search past conflicts right now."}


@router.post("/tools/get_partner_perspective")
async def tool_get_partner_perspective(request: Request):
    """Direct endpoint for get_partner_perspective tool."""
    try:
        body = await request.json()
        message = body.get("message", {})

        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})

        call = message.get("call", {})
        metadata = call.get("metadata", {})

        result = await get_partner_perspective_impl(
            situation_description=parameters.get("situation_description", ""),
            relationship_id=metadata.get("relationship_id", ""),
            partner_b_name=metadata.get("partner_b_name", "Partner B")
        )

        return {"result": result}

    except Exception as e:
        logger.error(f"Error in get_partner_perspective: {e}")
        return {"result": "I couldn't get that perspective right now."}
