"""
LLM service for Gemini 2.5 Flash via OpenRouter with structured output
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
    """Service for interacting with Gemini 2.5 Flash via OpenRouter with structured output using Pydantic models"""

    def __init__(self):
        # OpenRouter uses OpenAI-compatible API
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=60.0,  # Increased timeout for structured output generation
        )
        # Use Gemini 2.5 Flash for fast, cost-effective responses
        self.model = "google/gemini-2.5-flash"
        logger.info("✅ Initialized LLM service (Gemini 2.5 Flash via OpenRouter with Pydantic structured output)")
    
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

    def analyze_with_prompt(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Simple prompt-based analysis. Takes a prompt string and returns LLM response.
        Used by conflict_enrichment_service for extracting trigger phrases and unmet needs.
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
    
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
        """
        Generate structured output using Gemini 2.5 Flash with Pydantic models via OpenRouter.
        Uses JSON mode with strict schema enforcement.
        """
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
                    field_type = field_info.get("type", "")
                    if desc:
                        field_descriptions.append(f"- {field_name} ({field_type}): {desc}")
            
            schema_description = f"""
Model: {response_model.__name__}
Description: {model_doc}

Field Requirements:
{chr(10).join(field_descriptions)}

CRITICAL: You MUST respond with valid JSON that EXACTLY matches this schema.
All required fields must be present. Arrays must be arrays, strings must be strings.
"""
            
            # Add system message to enforce JSON output with schema details
            system_message = {
                "role": "system",
                "content": f"""You are a helpful assistant that generates structured JSON responses using Pydantic models.

You MUST respond ONLY with valid JSON matching this exact schema:

{schema_description}

Schema JSON:
{json.dumps(schema, indent=2)}

IMPORTANT:
- Return ONLY valid JSON, no markdown, no code blocks, no explanations
- All required fields must be present
- Arrays must be arrays of the correct type (e.g., List[str] means array of strings)
- Strings must be strings, not objects
- Follow the schema EXACTLY"""
            }
            
            # Prepend system message if not already present
            if messages[0].get("role") != "system":
                messages = [system_message] + messages
            
            # Use Gemini 2.5 Flash via OpenRouter with JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 4000,  # Increased for structured output
                response_format={"type": "json_object"}  # Force JSON mode
            )
            
            content = response.choices[0].message.content
            
            # Clean content - remove markdown code blocks if present
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # Parse JSON and validate with Pydantic
            data = json.loads(content)
            
            # Post-process data to fix common LLM mistakes
            data = self._fix_llm_output_format(data, response_model)
            
            return response_model(**data)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"Response content: {content[:1000] if content else 'None'}")
            raise
        except Exception as e:
            logger.error(f"❌ Error in structured output: {e}")
            if content:
                logger.error(f"Response content: {content[:1000]}")
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
        girlfriend_profile: Optional[str] = None,
        use_rag_context: bool = False
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
        
        # Determine if we're using RAG context or full transcript
        if use_rag_context:
            context_type = "RAG-retrieved relevant context from entire corpus (transcripts + profiles)"
            context_instruction = """
IMPORTANT: The following context includes:
- Relevant transcript chunks from the current conflict AND past conflicts (if patterns exist)
- Profile information about Adrian and Elara (personalities, backgrounds, values, communication styles)
- Cross-references between transcript events and profile traits

Use this ENTIRE corpus context to provide deep, empathetic, and contextualized analysis. Connect what was said to WHY it matters based on their profiles and past patterns.
"""
        else:
            context_type = "full transcript"
            context_instruction = ""
        
        logger.info(f"📝 Using {context_type}: {len(transcript_text)} characters, POV: {partner_id or 'neutral'}")
        
        prompt = f"""Analyze this relationship conflict with deep personalization from a specific partner's perspective.

Conflict ID: {conflict_id}

{gender_context}
{pov_context}
{profile_context}
{context_instruction}

{'RAG CONTEXT (Relevant chunks from entire corpus)' if use_rag_context else 'TRANSCRIPT'}:
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
        
        llm_start_msg = f"🚀 Calling Gemini 2.5 Flash for analysis (transcript: {len(transcript_text)} chars, POV: {partner_id or 'neutral'})"
        logger.info(llm_start_msg)
        print(llm_start_msg)  # Also print to stdout for visibility
        start_time = __import__('time').time()
        
        result = self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.7,
            max_tokens=1500  # Reduced from 2000 for faster generation (analysis typically needs ~800-1200 tokens)
        )
        
        elapsed = __import__('time').time() - start_time
        llm_timing_msg = f"✅ LLM analysis complete in {elapsed:.2f}s"
        logger.info(llm_timing_msg)
        print(llm_timing_msg)  # Also print to stdout for visibility
        return result
    
    def generate_repair_plan(
        self,
        transcript_text: str,
        conflict_id: str,
        partner_requesting: str,
        analysis_summary: str,
        response_model: Type[T],
        boyfriend_profile: Optional[str] = None,
        girlfriend_profile: Optional[str] = None,
        calendar_context: Optional[str] = None,
        messaging_context: Optional[str] = None  # NEW: Partner messaging insights
    ) -> T:
        """Generate personalized repair plan with gender-aware insights, calendar awareness, and messaging context"""
        
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
        
        # NEW: Add calendar context for timing awareness
        calendar_section = ""
        if calendar_context:
            calendar_section = f"""
CALENDAR & CYCLE AWARENESS (CRITICAL FOR TIMING):
{calendar_context}

TIMING GUIDANCE BASED ON CALENDAR:
- If Elara is in PMS/menstruation phase: Consider waiting a few days for the repair conversation, or be extra gentle and patient. Suggest comforting actions like getting her food or coffee instead of just avoiding the conversation.
- If upcoming anniversary/birthday: Could be a good opportunity to combine repair with celebration
- If high-risk cycle phase: Keep the conversation brief, focus on acknowledgment rather than problem-solving
- If low-risk phase (follicular/ovulation): Good time for deeper conversation and planning
- Consider predicted cycle dates when suggesting specific timing
"""

        # NEW: Add messaging context for communication-aware repair
        messaging_section = ""
        if messaging_context:
            messaging_section = f"""
PARTNER MESSAGING INSIGHTS (from recent text conversations):
{messaging_context}

Use messaging patterns to:
- Understand their current communication mood
- Reference positive interactions when building your approach
- Avoid communication patterns that have led to escalation
- Leverage repair attempts and bids for connection that have worked
"""

        # Use FULL transcript - no truncation
        logger.info(f"📝 Using full transcript for repair plan: {len(transcript_text)} characters")
        if calendar_context:
            logger.info(f"📅 Including calendar context: {len(calendar_context)} characters")
        if messaging_context:
            logger.info(f"💬 Including messaging context: {len(messaging_context)} characters")

        prompt = f"""Generate a HIGHLY PERSONALIZED repair plan for this SPECIFIC conflict and couple.

Conflict ID: {conflict_id}
Partner requesting help: {partner_requesting}

{gender_context}
{profile_context}
{calendar_section}
{messaging_section}

CONFLICT SUMMARY:
{analysis_summary}

TRANSCRIPT (for context):
{transcript_text}

REQUIREMENTS:
1. **Steps**: SPECIFIC actions for THIS couple. Reference actual issues from the transcript. Not generic advice - what should THIS person do?
2. **Apology Script**: PERSONALIZED to this conflict. Reference specific things said. If Boyfriend: direct, respectful, solution-focused. If Girlfriend: emotionally validating, shows care through details.
3. **Timing**: SPECIFIC to their situation. Consider their schedules, moods, when they're most receptive. 
   - **CRITICAL**: If calendar insights are provided, factor in cycle phase and upcoming events.
   - If calendar insights are NOT provided, do NOT invent date-related info.
   - If she's in a high-risk phase (PMS), suggest comforting actions (food, coffee) rather than avoiding the conversation.
4. **Risk Factors**: SPECIFIC things to avoid based on THIS conflict. What triggered escalation? What words/phrases should be avoided?
   - Include cycle-aware risks if applicable (e.g., "Avoid having this conversation during PMS phase")

Be SPECIFIC to this couple. Reference actual quotes and moments. Make it personal, not generic.
If calendar data shows a high-risk period, explicitly mention this in timing recommendations."""

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


    def generate_chat_response(
        self,
        user_message: str,
        rag_context: str,
        conversation_history: list[dict],
        system_prompt: str = "You are Luna, an empathetic relationship mediator."
    ) -> str:
        """Generate a chat response for the Luna interface"""
        try:
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add RAG context as system message
            if rag_context:
                messages.append({
                    "role": "system", 
                    "content": f"Relevant Context:\n{rag_context}"
                })
            
            # Add conversation history
            for msg in conversation_history:
                # Ensure role is valid (user, assistant, system)
                role = msg.get("role", "user")
                if role not in ["user", "assistant", "system"]:
                    role = "user"
                
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call LLM
            response = self.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            return response
        except Exception as e:
            logger.error(f"❌ Error generating chat response: {e}")
            return "I'm sorry, I'm having trouble processing your request right now."

    def generate_conflict_title(self, transcript_text: str) -> str:
        """Generate a concise, descriptive title for a conflict based on the transcript"""
        try:
            prompt = f"""Generate a short, descriptive title (3-6 words) for this conflict based on the transcript.
The title should capture the core issue.

TRANSCRIPT:
{transcript_text[:2000]}... (truncated)

TITLE REQUIREMENTS:
- 3-6 words maximum
- Descriptive but neutral
- Capture the main topic (e.g., "Argument about Holiday Plans", "Disagreement over Finances")
- No quotes or special characters
- Just the title text"""

            messages = [{"role": "user", "content": prompt}]
            
            title = self.chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=20
            )
            
            # Clean up title
            title = title.strip().strip('"').strip("'")
            return title
        except Exception as e:
            logger.error(f"❌ Error generating conflict title: {e}")
            return "Untitled Conflict"

    def generate_fight_debrief(
        self,
        transcript_text: str,
        conflict_id: str,
        relationship_id: str,
        response_model: Type[T],
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B",
        past_fights_summary: Optional[str] = None
    ) -> T:
        """
        Generate comprehensive post-fight debrief (Phase 3).
        Extracts repair attempts, escalation triggers, and resolution status.
        """
        past_context = ""
        if past_fights_summary:
            past_context = f"""
PAST FIGHTS CONTEXT (for pattern detection):
{past_fights_summary}

When analyzing this fight, compare it to past patterns:
- Does this topic recur?
- Are the same triggers causing escalation?
- Have repair attempts that worked before been tried again?
"""

        prompt = f"""Analyze this conflict transcript comprehensively to generate a Fight Debrief.

Conflict ID: {conflict_id}
Relationship ID: {relationship_id}
Partner A: {partner_a_name}
Partner B: {partner_b_name}

TRANSCRIPT:
{transcript_text}
{past_context}

ANALYSIS REQUIREMENTS:

1. **WHAT HAPPENED**:
   - topic: Main issue in 2-5 words
   - summary: What happened in 2-3 sentences
   - duration_estimate: Estimate the length (e.g., "15 minutes")
   - intensity_peak: 'low', 'medium', 'high', or 'explosive'
   - key_moments: 3-5 pivotal moments with approximate timestamps

2. **REPAIR DYNAMICS** (CRITICAL):
   For EVERY repair attempt in the transcript, identify:
   - Who made it (partner_a or partner_b)
   - What they said/did (quote if possible)
   - The action type: apologized, validated_feelings, took_responsibility, offered_solution, used_humor, physical_affection, asked_for_break, redirected_topic, expressed_love, other
   - The outcome: 'helped', 'hurt', or 'neutral'
   - What happened next (the evidence for the outcome)
   - Why it worked or failed

   Also identify:
   - who_initiated_repairs: 'partner_a', 'partner_b', 'both', or 'neither'
   - most_effective_moment: The moment that helped most (with quote)
   - most_damaging_moment: The moment that hurt most (with quote)

3. **RESOLUTION**:
   - resolution_status: 'resolved', 'unresolved', or 'temporary_truce'
   - what_resolved_it: If resolved, what worked
   - what_remains_unresolved: Issues still open

4. **LEARNINGS**:
   - phrases_to_avoid: Specific things said that made it worse
   - phrases_that_helped: Specific things said that helped
   - unmet_needs_partner_a: {partner_a_name}'s unmet needs
   - unmet_needs_partner_b: {partner_b_name}'s unmet needs
   - what_would_have_helped: What could have prevented escalation

5. **CONNECTION TO PAST** (if past context provided):
   - similar_to_past_topics: Topics from past fights this resembles
   - recurring_pattern_detected: If this follows a pattern seen before

Be SPECIFIC. Quote the transcript. Identify exact moments and phrases."""

        messages = [{"role": "user", "content": prompt}]

        logger.info(f"📊 Generating Fight Debrief for conflict {conflict_id}")
        start_time = __import__('time').time()

        result = self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.5,  # Lower temp for more accurate extraction
            max_tokens=3000  # Debriefs can be long
        )

        elapsed = __import__('time').time() - start_time
        logger.info(f"✅ Fight Debrief complete in {elapsed:.2f}s")
        return result

    def generate_personalized_repair_plan(
        self,
        transcript_text: str,
        conflict_id: str,
        requesting_partner: str,
        target_partner: str,
        response_model: Type[T],
        requesting_profile: Optional[str] = None,
        target_profile: Optional[str] = None,
        fight_debrief: Optional[str] = None,
        past_fights_intelligence: Optional[str] = None,
        calendar_context: Optional[str] = None,
        messaging_context: Optional[str] = None  # NEW: Partner messaging insights
    ) -> T:
        """
        Generate HIGHLY personalized repair plan with mandatory citations (Phase 2).

        ENHANCED: Now integrates messaging context from partner-to-partner messaging.

        Args:
            transcript_text: Full conflict transcript
            conflict_id: Conflict UUID
            requesting_partner: Name of partner initiating repair
            target_partner: Name of partner being approached
            response_model: Pydantic model for structured output
            requesting_profile: Full profile of requesting partner
            target_profile: Full profile of target partner (CRITICAL for personalization)
            fight_debrief: Summary of this fight's dynamics
            past_fights_intelligence: Patterns from past fights
            calendar_context: Cycle/calendar awareness
            messaging_context: Insights from partner messaging (sentiment trends, communication patterns)
        """
        # Build comprehensive context
        profile_context = ""
        if target_profile:
            profile_context += f"""
TARGET PARTNER PROFILE (CRITICAL - {target_partner}):
{target_profile}

PERSONALIZATION REQUIREMENTS based on {target_partner}'s profile:
- Check their post_conflict_need: Do they need 'space', 'connection', or 'depends'? CITE THIS.
- Check their apology_preferences: What makes an apology genuine to them? CITE THIS.
- Check their repair_gestures: What small gestures help? USE ONE OF THESE.
- Check their escalation_triggers: What makes things worse? AVOID THESE.
"""

        if requesting_profile:
            profile_context += f"""
REQUESTING PARTNER PROFILE ({requesting_partner}):
{requesting_profile}
"""

        debrief_context = ""
        if fight_debrief:
            debrief_context = f"""
THIS FIGHT'S DYNAMICS:
{fight_debrief}

Use repair attempts that worked. Avoid what made things worse.
"""

        history_context = ""
        if past_fights_intelligence:
            history_context = f"""
INTELLIGENCE FROM PAST FIGHTS:
{past_fights_intelligence}

Reference what has worked/failed in similar past conflicts.
"""

        calendar_section = ""
        if calendar_context:
            calendar_section = f"""
CALENDAR & CYCLE AWARENESS:
{calendar_context}
"""

        # NEW: Add messaging context
        messaging_section = ""
        if messaging_context:
            messaging_section = f"""
PARTNER MESSAGING INSIGHTS (from recent text conversations):
{messaging_context}

Use messaging patterns to:
- Understand their current communication mood
- Reference positive interactions when building your approach
- Avoid patterns that led to escalation in messages
"""

        prompt = f"""Generate a DEEPLY PERSONALIZED repair plan for {requesting_partner} approaching {target_partner}.

Conflict ID: {conflict_id}

TRANSCRIPT:
{transcript_text}

{profile_context}
{debrief_context}
{history_context}
{calendar_section}
{messaging_section}

CRITICAL REQUIREMENTS - EVERY recommendation must cite its source:

1. **TIMING (when_to_approach)**:
   - Check {target_partner}'s post_conflict_need profile field
   - If 'space': Recommend waiting, specify how long
   - If 'connection': Recommend approaching soon
   - If 'depends': Consider the fight intensity
   - MUST cite: "{target_partner}'s profile says they need [space/connection/depends]"

2. **STEPS** (3-6 action steps):
   Each step MUST include:
   - action: What to do
   - rationale: Why this helps
   - citation_type: 'profile', 'transcript', 'pattern', 'calendar', or 'messaging'
   - citation_detail: Specific quote/reference

3. **APOLOGY SCRIPT**:
   - Reference {target_partner}'s apology_preferences
   - Include acknowledgment of specific things from the transcript
   - MUST cite what makes apologies genuine to them

4. **SUGGESTED GESTURE**:
   - Pick ONE from {target_partner}'s repair_gestures list
   - If list is empty, suggest based on their soothing_mechanisms
   - MUST cite the profile field

5. **THINGS TO AVOID** (minimum 2):
   - Check {target_partner}'s escalation_triggers
   - Reference what escalated THIS fight from the transcript
   - Each must have citation_type and citation_detail

6. **LESSONS FROM PAST** (if history provided):
   - Reference similar past fights
   - What worked/failed before

7. **META ASSESSMENT**:
   - personalization_score: 'high' if you cited profile fields, 'medium' if mostly transcript, 'low' if generic
   - missing_data: List any profile fields that were empty/missing

REMEMBER: Every single recommendation must trace back to:
- A specific profile field (apology_preferences, post_conflict_need, repair_gestures, escalation_triggers)
- A specific transcript quote
- A pattern from past fights
- Calendar data
- Messaging patterns (sentiment trends, successful communication moments)

Generic advice = FAIL. Everything must be personalized and cited."""

        messages = [{"role": "user", "content": prompt}]

        logger.info(f"💝 Generating personalized repair plan for {requesting_partner} → {target_partner}")
        start_time = __import__('time').time()

        result = self.structured_output(
            messages=messages,
            response_model=response_model,
            temperature=0.7,
            max_tokens=3000
        )

        elapsed = __import__('time').time() - start_time
        logger.info(f"✅ Personalized repair plan complete in {elapsed:.2f}s")
        return result

    def extract_topics(self, transcript_text: str) -> list[str]:
        """Extract 1-3 specific topics from a conflict transcript"""
        try:
            class TopicResponse(BaseModel):
                topics: list[str]

            prompt = f"""Analyze this relationship conflict conversation and extract 1-3 specific topics/themes.

Examples of good topics:
- "Household Chores Distribution"
- "Quality Time Together"
- "Communication During Arguments"
- "Financial Planning"
- "Jealousy & Trust"

TRANSCRIPT:
{transcript_text[:5000]}... (truncated if too long)

REQUIREMENTS:
- Return ONLY a JSON array of topics
- 1-3 topics maximum
- Be specific but concise (2-5 words per topic)
- Focus on the underlying issues, not just surface arguments
"""

            messages = [{"role": "user", "content": prompt}]

            result = self.structured_output(
                messages=messages,
                response_model=TopicResponse,
                temperature=0.5,
                max_tokens=100
            )

            return result.topics
        except Exception as e:
            logger.error(f"❌ Error extracting topics: {e}")
            return ["Conflict Session"]

# Singleton instance
llm_service = LLMService()

