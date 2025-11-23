"""
LLM service for GPT-4o-mini via OpenRouter with structured output
"""
import logging
import json
from typing import Type, TypeVar, Optional
from openai import OpenAI
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMService:
    """Service for interacting with GPT-4o-mini via OpenRouter"""
    
    def __init__(self):
        # OpenRouter uses OpenAI-compatible API
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=30.0,  # 30 second timeout for faster API calls (GPT-4o-mini is fast)
        )
        self.model = "openai/gpt-4o-mini"
        logger.info("✅ Initialized LLM service (GPT-4o-mini via OpenRouter)")
    
    def chat_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Basic chat completion"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Error in chat completion: {e}")
            raise
    
    def chat_completion_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Streaming chat completion - yields text chunks as they're generated (sync generator)"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"❌ Error in streaming chat completion: {e}")
            raise
    
    def structured_output(
        self,
        messages: list,
        response_model: Type[T],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> T:
        """Generate structured output using JSON mode"""
        content = None
        try:
            # Build system message using Pydantic model docstrings and field descriptions
            schema = response_model.model_json_schema()
            model_doc = response_model.__doc__ or ""
            
            # Extract field descriptions from schema
            field_descriptions = []
            if "properties" in schema:
                for field_name, field_info in schema["properties"].items():
                    desc = field_info.get("description", "")
                    if desc:
                        field_descriptions.append(f"- {field_name}: {desc}")
            
            schema_description = f"""
Model: {response_model.__name__}
Description: {model_doc}

Field Requirements:
{chr(10).join(field_descriptions)}

You must respond in valid JSON format matching this exact schema.
"""
            
            # Add system message to enforce JSON output with schema details
            system_message = {
                "role": "system",
                "content": f"You are a helpful assistant that responds in valid JSON format matching this schema:\n\n{schema_description}\n\nSchema JSON: {json.dumps(schema, indent=2)}"
            }
            
            # Prepend system message if not already present
            if messages[0].get("role") != "system":
                messages = [system_message] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Parse JSON and validate with Pydantic
            data = json.loads(content)
            
            # Post-process data to fix common LLM mistakes
            data = self._fix_llm_output_format(data, response_model)
            
            return response_model(**data)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"Response content: {content}")
            raise
        except Exception as e:
            logger.error(f"❌ Error in structured output: {e}")
            if content:
                logger.error(f"Response content: {content[:500]}")
            raise
    
    def _fix_llm_output_format(self, data: dict, response_model: Type[T]) -> dict:
        """Fix common LLM output format issues"""
        # Fix communication_breakdowns if it's an array of objects instead of strings
        if "communication_breakdowns" in data and isinstance(data["communication_breakdowns"], list):
            fixed_breakdowns = []
            for item in data["communication_breakdowns"]:
                if isinstance(item, dict):
                    # Extract text from object - try common fields
                    text = item.get("breakdown") or item.get("moment") or item.get("description") or item.get("text") or str(item)
                    fixed_breakdowns.append(text)
                elif isinstance(item, str):
                    fixed_breakdowns.append(item)
                else:
                    fixed_breakdowns.append(str(item))
            data["communication_breakdowns"] = fixed_breakdowns
        
        return data
    
    def analyze_conflict(
        self,
        transcript_text: str,
        conflict_id: str,
        response_model: Type[T],
        partner_id: Optional[str] = None,  # "partner_a" (boyfriend) or "partner_b" (girlfriend)
        boyfriend_profile: Optional[str] = None,
        girlfriend_profile: Optional[str] = None
    ) -> T:
        """Analyze conflict transcript with structured output, personalized from a specific partner's POV"""
        
        # Determine which partner's perspective we're analyzing from
        is_boyfriend_pov = partner_id == "partner_a" if partner_id else None
        
        # Gender-aware context
        gender_context = """
IMPORTANT CONTEXT FOR ANALYSIS:
- Men typically need: Respect, appreciation, feeling competent, space to process, solutions
- Women typically need: To be heard, emotional connection, feeling cared for, attention to small details, validation of feelings
- These are general patterns - use partner profiles for specific personalization
"""
        
        # Build personalized profile context based on POV
        profile_context = ""
        pov_context = ""
        
        if is_boyfriend_pov is True:
            pov_context = """
ANALYZING FROM BOYFRIEND'S PERSPECTIVE:
- Focus on what HE experienced, felt, and needed
- Understand HIS triggers, HIS unmet needs, HIS communication style
- Consider HIS profile and personality traits
- What would HE say about this conflict? How did HE perceive what happened?
"""
            if boyfriend_profile:
                profile_context += f"\nBOYFRIEND'S PROFILE (Your Perspective):\n{boyfriend_profile}\n"
            if girlfriend_profile:
                profile_context += f"\nGIRLFRIEND'S PROFILE (Partner's Perspective):\n{girlfriend_profile}\n"
        elif is_boyfriend_pov is False:
            pov_context = """
ANALYZING FROM GIRLFRIEND'S PERSPECTIVE:
- Focus on what SHE experienced, felt, and needed
- Understand HER triggers, HER unmet needs, HER communication style
- Consider HER profile and personality traits
- What would SHE say about this conflict? How did SHE perceive what happened?
"""
            if girlfriend_profile:
                profile_context += f"\nGIRLFRIEND'S PROFILE (Your Perspective):\n{girlfriend_profile}\n"
            if boyfriend_profile:
                profile_context += f"\nBOYFRIEND'S PROFILE (Partner's Perspective):\n{boyfriend_profile}\n"
        else:
            # Neutral analysis (both perspectives)
            if boyfriend_profile:
                profile_context += f"\nBOYFRIEND'S PROFILE:\n{boyfriend_profile}\n"
            if girlfriend_profile:
                profile_context += f"\nGIRLFRIEND'S PROFILE:\n{girlfriend_profile}\n"
        
        # Use FULL transcript - no truncation
        logger.info(f"📝 Using full transcript: {len(transcript_text)} characters, POV: {partner_id or 'neutral'}")
        
        prompt = f"""Analyze this relationship conflict transcript with deep personalization from a specific partner's perspective.

Conflict ID: {conflict_id}

{gender_context}
{pov_context}
{profile_context}

TRANSCRIPT:
{transcript_text}

ANALYSIS REQUIREMENTS (Personalized from {partner_id or "both partners"} perspective):
1. **Fight Summary**: Be SPECIFIC to this couple. Reference actual things said, not generic advice. Write from the perspective of the partner whose POV you're analyzing.
2. **Root Causes**: Identify SPECIFIC underlying issues from THIS transcript. What are the REAL problems here? Consider what THIS partner would identify as root causes.
3. **Escalation Points**: Exact moments where things escalated - quote what was said. Focus on what triggered THIS partner.
4. **Unmet Needs**:
   - Boyfriend's unmet needs: Consider that men often need respect, appreciation, feeling heard without judgment. What SPECIFIC needs did he express? Analyze from HIS perspective.
   - Girlfriend's unmet needs: Consider that women often need to feel heard, emotional connection, care shown through actions. What SPECIFIC needs did she express? Analyze from HER perspective.
5. **Communication Breakdowns**: SPECIFIC moments where communication failed - what was said, what was misunderstood? Return as an array of STRINGS, not objects. Focus on breakdowns from THIS partner's perspective.

IMPORTANT: Return communication_breakdowns as an array of strings (not objects). Example: ["Adrian assumed Elara was criticizing him when she was just expressing concern", "Elara felt dismissed when Adrian changed the subject"]

Be SPECIFIC to this couple and this conflict. Reference actual quotes and moments from the transcript. Write the analysis from the perspective of the partner whose POV you're analyzing."""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        logger.info(f"🚀 Calling GPT-4o-mini for analysis (transcript: {len(transcript_text)} chars, POV: {partner_id or 'neutral'})")
        start_time = __import__('time').time()
        
        result = self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.7,
            max_tokens=2000
        )
        
        elapsed = __import__('time').time() - start_time
        logger.info(f"✅ LLM analysis complete in {elapsed:.2f}s")
        return result
    
    def generate_repair_plan(
        self,
        transcript_text: str,
        conflict_id: str,
        partner_requesting: str,
        analysis_summary: str,
        response_model: Type[T],
        boyfriend_profile: Optional[str] = None,
        girlfriend_profile: Optional[str] = None
    ) -> T:
        """Generate personalized repair plan with gender-aware insights"""
        
        # Determine which partner is requesting
        is_boyfriend_requesting = partner_requesting.lower() in ["boyfriend", "partner_a", "partner a"]
        
        gender_context = """
GENDER-AWARE REPAIR GUIDANCE:
- If Boyfriend is apologizing: Men often respond well to direct, respectful communication. Show you value his perspective. Avoid being overly emotional - be clear and solution-focused.
- If Girlfriend is apologizing: Women often need to feel heard first. Show emotional understanding, validate feelings, demonstrate care through specific actions.

- When approaching Boyfriend: Respect his need to process. Give space if needed. Be direct about what you want to discuss.
- When approaching Girlfriend: Show you've been listening. Pay attention to small details she mentioned. Demonstrate care through actions, not just words.
"""
        
        profile_context = ""
        if boyfriend_profile:
            profile_context += f"\nBOYFRIEND'S PROFILE:\n{boyfriend_profile}\n"
        if girlfriend_profile:
            profile_context += f"\nGIRLFRIEND'S PROFILE:\n{girlfriend_profile}\n"
        
        # Use FULL transcript - no truncation
        logger.info(f"📝 Using full transcript for repair plan: {len(transcript_text)} characters")
        
        prompt = f"""Generate a HIGHLY PERSONALIZED repair plan for this SPECIFIC conflict and couple.

Conflict ID: {conflict_id}
Partner requesting help: {partner_requesting}

{gender_context}
{profile_context}

CONFLICT SUMMARY:
{analysis_summary}

TRANSCRIPT (for context):
{transcript_text}

REQUIREMENTS:
1. **Steps**: SPECIFIC actions for THIS couple. Reference actual issues from the transcript. Not generic advice - what should THIS person do?
2. **Apology Script**: PERSONALIZED to this conflict. Reference specific things said. If Boyfriend: direct, respectful, solution-focused. If Girlfriend: emotionally validating, shows care through details.
3. **Timing**: SPECIFIC to their situation. Consider their schedules, moods, when they're most receptive.
4. **Risk Factors**: SPECIFIC things to avoid based on THIS conflict. What triggered escalation? What words/phrases should be avoided?

Be SPECIFIC to this couple. Reference actual quotes and moments. Make it personal, not generic."""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        logger.info(f"💝 Starting repair plan generation for {partner_requesting}")
        start_time = __import__('time').time()
        
        result = self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.7,
            max_tokens=2000
        )
        
        elapsed = __import__('time').time() - start_time
        logger.info(f"✅ Repair plan complete in {elapsed:.2f}s")
        return result
        
        return self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.7,
            max_tokens=2000
        )

# Singleton instance
llm_service = LLMService()

