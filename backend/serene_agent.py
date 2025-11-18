"""Serene: Warm relationship mediator with LLM + RAG intelligence."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import httpx

from .rag_handler import get_amara_context

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# OpenRouter configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-4o-mini"

# Backend configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Serene's system prompt
SERENE_SYSTEM_PROMPT = """You are Serene, a warm, empathetic relationship mediator and couples therapist.

## Your Core Purpose
Help people (specifically Amara's boyfriend) understand their partner better. Translate emotional contexts into logical explanations. Be the bridge between hearts and minds.

## Your Personality
- Warm, caring, genuine (like a trusted friend who's also a therapist)
- Patient and never judgmental
- Deeply empathetic but also practical
- You validate feelings BEFORE offering solutions
- You listen more than you speak
- You ask clarifying questions to understand deeply

## How to Respond
1. **Listen first** - Ask clarifying questions
2. **Validate** - Acknowledge their feelings
3. **Explain** - Help them understand Amara's perspective
4. **Coach** - Suggest specific things to say/do
5. **Empower** - Leave them feeling capable

## About Amara
Reference the context provided below about Amara. Use her real preferences, values, and communication style when coaching.

## Communication Style
- Speak warmly but directly
- Use "I" statements to validate
- Ask questions more than give advice
- Suggest one or two concrete actions, not five
- Reference specific things about Amara when helpful

## Your Mission
Make people feel UNDERSTOOD. Leave them saying: "Oh, I finally get it. Thank you."
"""


class SereneAgent:
    """Serene: Relationship mediator powered by LLM + RAG."""

    def __init__(self):
        self.conversation_history: list[dict] = []
        self.amara_context: dict = self._load_amara_profile()

    def _load_amara_profile(self) -> dict:
        """Load Amara's profile from the knowledge base."""
        return {
            "name": "Amara",
            "personality": "Warm, thoughtful, quiet strength",
            "heritage": ["Kerala (primary)", "Trinidad & Tobago", "Tanzania"],
            "favorite_colors": ["sunflower yellow", "bright turquoise", "deep green"],
            "favorite_flowers": ["marigold", "wildflowers", "jasmine"],
            "favorite_foods": ["coconut rice", "spicy mango pickle", "crisp samosas", "pilau rice", "fresh fruit with lime"],
            "favorite_places": ["sunny park", "home nook by window", "city market", "seaside walk at sunset"],
            "values": ["authenticity", "respect", "thoughtfulness", "order & beauty"],
            "triggers": ["feeling unheard", "being dismissed", "logical answers when needing validation"],
            "pet_peeves": ["dismissiveness", "rudeness", "interrupting", "boundary-crossing", "gossip", "loud chewing"],
            "communication_style": "Emotional validation before logical solutions",
        }

    async def process_message(self, user_message: str) -> str:
        """Process user message and generate Serene's response with RAG context."""
        logger.info(f"Processing message: {user_message}")

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        try:
            # Get relevant context about Amara from RAG
            amara_context = await get_amara_context(user_message)
            
            # Build the system prompt with Amara's context
            system_prompt = SERENE_SYSTEM_PROMPT
            if amara_context:
                system_prompt += f"\n\n{amara_context}"

            # Call OpenRouter
            response = httpx.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": BACKEND_URL,
                    "X-Title": "Serene Voice Agent",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        *self.conversation_history,
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                timeout=30.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result["choices"][0]["message"]["content"]
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message,
                })
                
                logger.info(f"Generated response: {assistant_message[:100]}...")
                return assistant_message
            else:
                logger.error(f"OpenRouter error: {response.status_code} - {response.text}")
                return "I'm sorry, I'm having trouble understanding. Can you tell me more about what happened?"

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I'm having trouble understanding. Can you tell me more about what happened?"

    def reset_conversation(self) -> None:
        """Reset conversation history for a new call."""
        self.conversation_history = []
        logger.info("Conversation reset")


# Global instance
serene = SereneAgent()


async def get_serene_response(user_message: str) -> str:
    """Convenience function to get Serene's response."""
    return await serene.process_message(user_message)
