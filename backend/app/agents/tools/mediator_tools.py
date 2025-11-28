import os
import json
import time
import logging
import asyncio
from typing import Annotated, Dict, List, Optional, Any
from datetime import datetime, timedelta

from livekit.agents import llm
from langfuse import observe

# Import services (using lazy imports inside functions to avoid circular deps if any)
# But typically safe to import at top if structured correctly
try:
    from app.services.pinecone_service import pinecone_service
    from app.services.embeddings_service import embeddings_service
except ImportError:
    pinecone_service = None
    embeddings_service = None

# Configure logger
logger = logging.getLogger("mediator-tools")

# Simple in-memory cache
_cache: Dict[str, Any] = {}
_cache_ttl = int(os.getenv("TOOL_CACHE_TTL_SECONDS", "300"))

def _get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return data
        else:
            del _cache[key]
    return None

def _set_cache(key: str, value: Any):
    _cache[key] = (value, time.time())

class MediatorTools:
    """Tools for the Luna Mediator Agent"""

    def __init__(self, conflict_id: str, relationship_id: str):
        self.conflict_id = conflict_id
        self.relationship_id = relationship_id
        
        # Initialize OpenAI client for internal tool use (Elara perspective)
        try:
            from openai import AsyncOpenAI
            self.openai = AsyncOpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
        except Exception as e:
            logger.error(f"Failed to init OpenAI for tools: {e}")
            self.openai = None

    @observe(name="find_similar_conflicts")
    async def find_similar_conflicts(self, topic_keywords: str) -> str:
        """
        Find similar past conflicts to see patterns. Returns a summary of what happened before.
        
        Args:
            topic_keywords: Keywords describing the current conflict topic
        """
        cache_key = f"similar_conflicts:{self.conflict_id}:{topic_keywords}"
        cached = _get_cached(cache_key)
        if cached:
            logger.info(f"Using cached similar conflicts for {topic_keywords}")
            return cached

        if not pinecone_service or not embeddings_service:
            return "I'm having trouble accessing your conflict history right now."

        try:
            logger.info(f"Searching for conflicts similar to: {topic_keywords}")
            
            # Generate embedding for the query
            query_embedding = embeddings_service.embed_query(topic_keywords)
            
            # Query Pinecone
            # Assuming 'conflict_summaries' or similar namespace, or using the main index with filter
            # Based on mediator_agent.py, it seems we use 'transcript_chunks' but maybe we should look for summaries if available
            # For now, let's assume we search for similar conversations in 'transcript_chunks' or a 'conflicts' namespace if it exists.
            # The user mentioned 'conflict_summaries' namespace in the plan discussion.
            
            results = await asyncio.to_thread(
                pinecone_service.index.query,
                vector=query_embedding,
                top_k=5,
                namespace="conflict_summaries", # Assuming this namespace exists as discussed
                filter={
                    "relationship_id": {"$eq": self.relationship_id},
                    "conflict_id": {"$ne": self.conflict_id} # Exclude current
                },
                include_metadata=True
            )
            
            if not results or not results.matches:
                # Fallback to transcript chunks if summaries not found
                results = await asyncio.to_thread(
                    pinecone_service.index.query,
                    vector=query_embedding,
                    top_k=5,
                    namespace="transcript_chunks",
                    filter={
                        "relationship_id": {"$eq": self.relationship_id},
                        "conflict_id": {"$ne": self.conflict_id}
                    },
                    include_metadata=True
                )

            if not results or not results.matches:
                response = "I couldn't find any similar past conflicts in your history."
                _set_cache(cache_key, response)
                return response

            # Process results
            # Group by conflict_id to avoid duplicates
            unique_conflicts = {}
            for match in results.matches:
                cid = match.metadata.get("conflict_id")
                if cid and cid not in unique_conflicts:
                    unique_conflicts[cid] = match.metadata
            
            # Take top 3
            top_conflicts = list(unique_conflicts.values())[:3]
            
            if not top_conflicts:
                response = "I didn't find any clear matches in your past conflicts."
                _set_cache(cache_key, response)
                return response

            # Format response
            response_parts = ["Here are some similar conflicts I found:"]
            
            for c in top_conflicts:
                date_str = c.get("date", "Unknown date")
                # Try to parse date if it's a timestamp or string
                topic = c.get("topic", c.get("text", "Unknown topic")[:50] + "...")
                status = c.get("status", "resolved" if c.get("resolved") else "unresolved")
                
                response_parts.append(f"- On {date_str}, you discussed '{topic}'. Status: {status}.")
            
            response = "\n".join(response_parts)
            
            # Telemetry handled by @observe decorator
            
            _set_cache(cache_key, response)
            return response

        except Exception as e:
            logger.error(f"Error in find_similar_conflicts: {e}")
            return "I encountered an error while looking up past conflicts."

    @observe(name="get_elara_perspective")
    async def get_elara_perspective(self, situation_description: str) -> str:
        """
        Get Elara's likely perspective on the current situation based on her profile.
        
        Args:
            situation_description: Description of the specific situation or behavior to analyze
        """
        cache_key = f"elara_perspective:{self.conflict_id}:{situation_description}"
        cached = _get_cached(cache_key)
        if cached:
            logger.info(f"Using cached Elara perspective for {situation_description}")
            return cached

        if not self.openai:
            return "I can't access the perspective analysis tool right now."

        try:
            logger.info(f"Generating Elara perspective for: {situation_description}")
            
            # 1. Fetch Elara's profile (simplified for now, ideally fetch from DB/Pinecone)
            # For this implementation, we'll try to fetch from Pinecone 'profiles' namespace
            profile_text = ""
            if pinecone_service and embeddings_service:
                # Search for Elara's profile
                query_embedding = embeddings_service.embed_query("Elara Voss personality triggers communication style")
                results = await asyncio.to_thread(
                    pinecone_service.index.query,
                    vector=query_embedding,
                    top_k=3,
                    namespace="profiles",
                    filter={"person_name": {"$eq": "Elara Voss"}}, # Assuming metadata has name
                    include_metadata=True
                )
                if results and results.matches:
                    profile_text = "\n".join([m.metadata.get("text", "") for m in results.matches])
            
            if not profile_text:
                # Fallback if no profile found in vector DB, use a generic placeholder or try to get from context
                # But we really need profile data. Let's assume we have some basic info or fail gracefully.
                # Ideally we'd pass the profile in __init__ if available.
                # For now, let's proceed with a generic prompt if empty, or better, return a message.
                pass 

            # 2. Generate perspective using LLM
            system_prompt = """
            You are an empathetic relationship psychologist. 
            Based on Elara's profile, explain how she is likely perceiving the described situation.
            Focus on her triggers, values, and communication style.
            Keep it concise (2-3 sentences) and speak as if you are explaining it to her partner.
            Do not judge, just explain her likely internal state.
            """
            
            user_prompt = f"""
            Profile Excerpt:
            {profile_text}
            
            Situation:
            {situation_description}
            
            What is Elara likely thinking and feeling?
            """
            
            completion = await self.openai.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            perspective = completion.choices[0].message.content
            
            # Telemetry handled by @observe decorator
            
            _set_cache(cache_key, perspective)
            return perspective

        except Exception as e:
            logger.error(f"Error in get_elara_perspective: {e}")
            return "I'm having trouble analyzing Elara's perspective right now."
