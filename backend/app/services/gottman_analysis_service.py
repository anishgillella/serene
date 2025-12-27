"""
Gottman Analysis Service
Extracts Four Horsemen, repair attempts, and communication patterns from conflict transcripts
Based on Dr. John Gottman's research on relationship health predictors
"""
import logging
import json
import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.llm_service import llm_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Structured LLM Output
# ============================================================================

class HorsemanInstance(BaseModel):
    """A single instance of a Four Horseman behavior"""
    speaker: str = Field(description="Who exhibited this behavior: 'partner_a' or 'partner_b'")
    quote: str = Field(description="The exact quote or description from the transcript")
    severity: int = Field(description="Severity from 1-10", ge=1, le=10)
    horseman_type: Optional[str] = Field(default=None, description="For contempt: 'sarcasm', 'mockery', 'name_calling', 'superiority'")


class HorsemanScore(BaseModel):
    """Score and instances for one of the Four Horsemen"""
    score: int = Field(description="Overall score from 0-10", ge=0, le=10)
    instances: List[HorsemanInstance] = Field(default_factory=list)


class FourHorsemen(BaseModel):
    """The Four Horsemen of relationship apocalypse"""
    criticism: HorsemanScore = Field(description="Character attacks, 'You always/never' statements")
    contempt: HorsemanScore = Field(description="Mockery, sarcasm, name-calling, eye-rolling, superiority")
    defensiveness: HorsemanScore = Field(description="Counter-complaints, playing victim, deflection")
    stonewalling: HorsemanScore = Field(description="Withdrawal, shutdown, silent treatment")


class RepairAttempt(BaseModel):
    """An attempt to de-escalate or repair the conversation"""
    speaker: str = Field(description="Who made the repair: 'partner_a' or 'partner_b'")
    repair_type: str = Field(description="Type: 'humor', 'acknowledgment', 'de_escalation', 'affection', 'apology', 'reframe', 'break_request'")
    quote: str = Field(description="The quote or description of the repair attempt")
    successful: bool = Field(description="Did the partner accept/respond positively?")
    partner_response: Optional[str] = Field(default=None, description="How the partner responded")


class CommunicationMetrics(BaseModel):
    """Communication quality metrics"""
    partner_a_i_statements: int = Field(default=0, description="Count of 'I feel...' statements by partner A")
    partner_a_you_statements: int = Field(default=0, description="Count of 'You always/never...' statements by partner A")
    partner_b_i_statements: int = Field(default=0, description="Count of 'I feel...' statements by partner B")
    partner_b_you_statements: int = Field(default=0, description="Count of 'You always/never...' statements by partner B")
    interruptions: int = Field(default=0, description="Number of interruptions detected")
    active_listening_instances: int = Field(default=0, description="Instances of reflection, validation, paraphrasing")


class EmotionalFlooding(BaseModel):
    """Detection of emotional flooding (physiological overwhelm)"""
    detected: bool = Field(default=False, description="Was flooding detected?")
    affected_partner: Optional[str] = Field(default=None, description="'partner_a', 'partner_b', 'both', or null")
    indicators: List[str] = Field(default_factory=list, description="Signs of flooding observed")


class OverallAssessment(BaseModel):
    """Overall assessment of the conflict"""
    primary_issue: str = Field(description="Brief description of the core issue")
    most_concerning_horseman: Optional[str] = Field(default=None, description="Which horseman was most present")
    repair_effectiveness: str = Field(description="'high', 'medium', 'low', or 'none_attempted'")
    recommended_focus: str = Field(description="What this couple should work on")


class GottmanAnalysisResult(BaseModel):
    """Complete Gottman analysis of a conflict"""
    four_horsemen: FourHorsemen
    repair_attempts: List[RepairAttempt] = Field(default_factory=list)
    communication: CommunicationMetrics
    emotional_flooding: EmotionalFlooding
    positive_interactions: int = Field(default=0)
    negative_interactions: int = Field(default=0)
    overall_assessment: OverallAssessment


# ============================================================================
# Gottman Analysis Service
# ============================================================================

class GottmanAnalysisService:
    """
    Service for analyzing conflict transcripts using Gottman's research framework.

    Detects:
    - Four Horsemen (Criticism, Contempt, Defensiveness, Stonewalling)
    - Repair Attempts and their success rate
    - Communication quality (I vs You statements)
    - Emotional flooding
    """

    def __init__(self):
        self.model_version = "gpt-4o-mini"
        logger.info("✅ Initialized Gottman Analysis Service")

    async def analyze_conflict(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> Dict[str, Any]:
        """
        Perform full Gottman analysis on a conflict transcript.

        Args:
            conflict_id: The conflict UUID
            transcript: Full transcript text
            relationship_id: The relationship UUID
            partner_a_name: Display name for partner A
            partner_b_name: Display name for partner B

        Returns:
            Dict containing all Gottman metrics
        """
        try:
            logger.info(f"🔬 Starting Gottman analysis for conflict {conflict_id}")

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(transcript, partner_a_name, partner_b_name)

            # Call LLM for structured analysis
            result = await asyncio.to_thread(
                self._call_llm_for_analysis,
                prompt
            )

            if not result:
                logger.warning(f"⚠️ LLM returned no result for conflict {conflict_id}")
                result = self._default_analysis()

            # Save to database
            await self._save_analysis(conflict_id, relationship_id, result)

            logger.info(
                f"✅ Gottman analysis complete for {conflict_id}: "
                f"Horsemen total={self._calculate_horsemen_total(result)}, "
                f"Repairs={len(result.get('repair_attempts', []))}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error in Gottman analysis for {conflict_id}: {str(e)}")
            raise

    def _build_analysis_prompt(
        self,
        transcript: str,
        partner_a_name: str,
        partner_b_name: str
    ) -> str:
        """Build the LLM prompt for Gottman analysis"""

        # Truncate very long transcripts
        max_chars = 6000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "\n... [transcript truncated for analysis]"

        prompt = f"""Analyze this conflict transcript using Dr. John Gottman's research-backed relationship framework.

TRANSCRIPT:
{transcript}

SPEAKER KEY:
- Partner A / partner_a: {partner_a_name}
- Partner B / partner_b: {partner_b_name}

Analyze for:

1. FOUR HORSEMEN OF THE APOCALYPSE (relationship destroyers):
   - CRITICISM: Character attacks, "You always...", "You never...", "What's wrong with you?"
   - CONTEMPT: Sarcasm, mockery, name-calling, eye-rolling, hostile humor, superiority, disgust
   - DEFENSIVENESS: Counter-complaints, "It's not my fault", playing victim, "yes-but" responses
   - STONEWALLING: Withdrawal, silent treatment, shutting down, "I'm done talking"

2. REPAIR ATTEMPTS: Any effort to de-escalate
   - Humor or levity
   - Acknowledgment of partner's feelings
   - Apologies (even partial)
   - Affection references
   - Suggesting a break
   - Reframing the issue
   Note if the repair was ACCEPTED (successful) or REJECTED

3. COMMUNICATION QUALITY:
   - "I" statements (healthy): "I feel hurt when..."
   - "You" statements (unhealthy): "You always...", "You make me..."
   - Interruptions
   - Active listening (reflection, validation)

4. EMOTIONAL FLOODING: Signs of physiological overwhelm
   - Rapid escalation
   - Shouting/caps
   - Extreme statements
   - Shutdown after escalation

Provide your analysis as valid JSON matching this exact structure:

{{
  "four_horsemen": {{
    "criticism": {{
      "score": 0-10,
      "instances": [{{"speaker": "partner_a|partner_b", "quote": "exact quote", "severity": 1-10}}]
    }},
    "contempt": {{
      "score": 0-10,
      "instances": [{{"speaker": "partner_a|partner_b", "quote": "exact quote", "severity": 1-10, "horseman_type": "sarcasm|mockery|name_calling|superiority"}}]
    }},
    "defensiveness": {{
      "score": 0-10,
      "instances": [{{"speaker": "partner_a|partner_b", "quote": "exact quote", "severity": 1-10}}]
    }},
    "stonewalling": {{
      "score": 0-10,
      "instances": [{{"speaker": "partner_a|partner_b", "quote": "description of withdrawal", "severity": 1-10}}]
    }}
  }},
  "repair_attempts": [
    {{
      "speaker": "partner_a|partner_b",
      "repair_type": "humor|acknowledgment|de_escalation|affection|apology|reframe|break_request",
      "quote": "the repair attempt",
      "successful": true|false,
      "partner_response": "how partner responded"
    }}
  ],
  "communication": {{
    "partner_a_i_statements": number,
    "partner_a_you_statements": number,
    "partner_b_i_statements": number,
    "partner_b_you_statements": number,
    "interruptions": number,
    "active_listening_instances": number
  }},
  "emotional_flooding": {{
    "detected": true|false,
    "affected_partner": "partner_a|partner_b|both|null",
    "indicators": ["list of signs"]
  }},
  "positive_interactions": number,
  "negative_interactions": number,
  "overall_assessment": {{
    "primary_issue": "brief description of core conflict",
    "most_concerning_horseman": "criticism|contempt|defensiveness|stonewalling|null",
    "repair_effectiveness": "high|medium|low|none_attempted",
    "recommended_focus": "what this couple should work on"
  }}
}}

IMPORTANT GUIDELINES:
- Contempt is the #1 predictor of divorce - be especially attentive to it
- Score 0 means the horseman was not present at all
- Score 10 means extreme, pervasive use of that horseman
- Be generous in identifying repair attempts - they're crucial for relationship health
- Return ONLY valid JSON, no other text or markdown

Return your analysis:"""

        return prompt

    def _call_llm_for_analysis(self, prompt: str) -> Dict[str, Any]:
        """Call LLM and parse the response"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert relationship therapist trained in Dr. John Gottman's methods. Analyze conflict transcripts with precision and empathy. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = llm_service.chat_completion(
                messages=messages,
                temperature=0.3,  # Lower temp for more consistent analysis
                max_tokens=2000
            )

            # Parse JSON from response
            return self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"❌ LLM call failed: {str(e)}")
            return self._default_analysis()

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return self._default_analysis()

            json_str = json_match.group()
            data = json.loads(json_str)

            # Validate required fields
            if "four_horsemen" not in data:
                logger.warning("Missing four_horsemen in response")
                return self._default_analysis()

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {str(e)}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when LLM fails"""
        return {
            "four_horsemen": {
                "criticism": {"score": 0, "instances": []},
                "contempt": {"score": 0, "instances": []},
                "defensiveness": {"score": 0, "instances": []},
                "stonewalling": {"score": 0, "instances": []}
            },
            "repair_attempts": [],
            "communication": {
                "partner_a_i_statements": 0,
                "partner_a_you_statements": 0,
                "partner_b_i_statements": 0,
                "partner_b_you_statements": 0,
                "interruptions": 0,
                "active_listening_instances": 0
            },
            "emotional_flooding": {
                "detected": False,
                "affected_partner": None,
                "indicators": []
            },
            "positive_interactions": 0,
            "negative_interactions": 0,
            "overall_assessment": {
                "primary_issue": "Unable to analyze",
                "most_concerning_horseman": None,
                "repair_effectiveness": "none_attempted",
                "recommended_focus": "General communication improvement"
            }
        }

    def _calculate_horsemen_total(self, result: Dict[str, Any]) -> int:
        """Calculate total Four Horsemen score"""
        fh = result.get("four_horsemen", {})
        return sum([
            fh.get("criticism", {}).get("score", 0),
            fh.get("contempt", {}).get("score", 0),
            fh.get("defensiveness", {}).get("score", 0),
            fh.get("stonewalling", {}).get("score", 0)
        ])

    async def _save_analysis(
        self,
        conflict_id: str,
        relationship_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Save Gottman analysis to database"""
        try:
            fh = result.get("four_horsemen", {})
            comm = result.get("communication", {})
            flooding = result.get("emotional_flooding", {})
            assessment = result.get("overall_assessment", {})
            repairs = result.get("repair_attempts", [])

            # Calculate repair success
            successful_repairs = sum(1 for r in repairs if r.get("successful", False))

            # Separate partner horsemen instances
            partner_a_horsemen = []
            partner_b_horsemen = []

            for horseman_type in ["criticism", "contempt", "defensiveness", "stonewalling"]:
                for instance in fh.get(horseman_type, {}).get("instances", []):
                    instance_data = {**instance, "type": horseman_type}
                    if instance.get("speaker") == "partner_a":
                        partner_a_horsemen.append(instance_data)
                    else:
                        partner_b_horsemen.append(instance_data)

            await asyncio.to_thread(
                self._save_to_db,
                conflict_id,
                relationship_id,
                fh,
                repairs,
                successful_repairs,
                comm,
                flooding,
                assessment,
                partner_a_horsemen,
                partner_b_horsemen,
                result
            )

        except Exception as e:
            logger.error(f"❌ Error saving Gottman analysis: {str(e)}")
            raise

    def _save_to_db(
        self,
        conflict_id: str,
        relationship_id: str,
        fh: Dict,
        repairs: List,
        successful_repairs: int,
        comm: Dict,
        flooding: Dict,
        assessment: Dict,
        partner_a_horsemen: List,
        partner_b_horsemen: List,
        raw_result: Dict
    ) -> None:
        """Synchronous database save"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO gottman_analysis (
                            conflict_id, relationship_id,
                            criticism_score, contempt_score, defensiveness_score, stonewalling_score,
                            partner_a_horsemen, partner_b_horsemen,
                            repair_attempts_count, successful_repairs_count, repair_attempt_details,
                            partner_a_i_statements, partner_a_you_statements,
                            partner_b_i_statements, partner_b_you_statements,
                            interruption_count, active_listening_instances,
                            emotional_flooding_detected, flooding_partner,
                            positive_interactions, negative_interactions,
                            primary_issue, most_concerning_horseman, repair_effectiveness, recommended_focus,
                            analyzed_at, model_version, raw_llm_response
                        ) VALUES (
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s
                        )
                        ON CONFLICT (conflict_id) DO UPDATE SET
                            criticism_score = EXCLUDED.criticism_score,
                            contempt_score = EXCLUDED.contempt_score,
                            defensiveness_score = EXCLUDED.defensiveness_score,
                            stonewalling_score = EXCLUDED.stonewalling_score,
                            partner_a_horsemen = EXCLUDED.partner_a_horsemen,
                            partner_b_horsemen = EXCLUDED.partner_b_horsemen,
                            repair_attempts_count = EXCLUDED.repair_attempts_count,
                            successful_repairs_count = EXCLUDED.successful_repairs_count,
                            repair_attempt_details = EXCLUDED.repair_attempt_details,
                            partner_a_i_statements = EXCLUDED.partner_a_i_statements,
                            partner_a_you_statements = EXCLUDED.partner_a_you_statements,
                            partner_b_i_statements = EXCLUDED.partner_b_i_statements,
                            partner_b_you_statements = EXCLUDED.partner_b_you_statements,
                            interruption_count = EXCLUDED.interruption_count,
                            active_listening_instances = EXCLUDED.active_listening_instances,
                            emotional_flooding_detected = EXCLUDED.emotional_flooding_detected,
                            flooding_partner = EXCLUDED.flooding_partner,
                            positive_interactions = EXCLUDED.positive_interactions,
                            negative_interactions = EXCLUDED.negative_interactions,
                            primary_issue = EXCLUDED.primary_issue,
                            most_concerning_horseman = EXCLUDED.most_concerning_horseman,
                            repair_effectiveness = EXCLUDED.repair_effectiveness,
                            recommended_focus = EXCLUDED.recommended_focus,
                            analyzed_at = EXCLUDED.analyzed_at,
                            raw_llm_response = EXCLUDED.raw_llm_response,
                            updated_at = NOW();
                    """, (
                        conflict_id, relationship_id,
                        fh.get("criticism", {}).get("score", 0),
                        fh.get("contempt", {}).get("score", 0),
                        fh.get("defensiveness", {}).get("score", 0),
                        fh.get("stonewalling", {}).get("score", 0),
                        json.dumps(partner_a_horsemen),
                        json.dumps(partner_b_horsemen),
                        len(repairs),
                        successful_repairs,
                        json.dumps(repairs),
                        comm.get("partner_a_i_statements", 0),
                        comm.get("partner_a_you_statements", 0),
                        comm.get("partner_b_i_statements", 0),
                        comm.get("partner_b_you_statements", 0),
                        comm.get("interruptions", 0),
                        comm.get("active_listening_instances", 0),
                        flooding.get("detected", False),
                        flooding.get("affected_partner"),
                        raw_result.get("positive_interactions", 0),
                        raw_result.get("negative_interactions", 0),
                        assessment.get("primary_issue", ""),
                        assessment.get("most_concerning_horseman"),
                        assessment.get("repair_effectiveness", "none_attempted"),
                        assessment.get("recommended_focus", ""),
                        datetime.now(),
                        self.model_version,
                        json.dumps(raw_result)
                    ))
                    conn.commit()

            logger.info(f"💾 Saved Gottman analysis for conflict {conflict_id}")

        except Exception as e:
            logger.error(f"❌ Database error saving Gottman analysis: {str(e)}")
            raise

    async def get_relationship_scores(
        self,
        relationship_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get aggregated Gottman scores for a relationship"""
        try:
            return await asyncio.to_thread(
                self._get_relationship_scores_sync,
                relationship_id
            )
        except Exception as e:
            logger.error(f"❌ Error getting relationship scores: {str(e)}")
            return None

    def _get_relationship_scores_sync(self, relationship_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous fetch of relationship scores"""
        try:
            from psycopg2.extras import RealDictCursor

            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT *
                        FROM gottman_relationship_scores
                        WHERE relationship_id = %s;
                    """, (relationship_id,))

                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Error fetching relationship scores: {str(e)}")
            return None

    async def get_conflict_analysis(
        self,
        conflict_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get Gottman analysis for a specific conflict"""
        try:
            return await asyncio.to_thread(
                self._get_conflict_analysis_sync,
                conflict_id
            )
        except Exception as e:
            logger.error(f"❌ Error getting conflict analysis: {str(e)}")
            return None

    def _get_conflict_analysis_sync(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous fetch of conflict analysis"""
        try:
            from psycopg2.extras import RealDictCursor

            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT *
                        FROM gottman_analysis
                        WHERE conflict_id = %s;
                    """, (conflict_id,))

                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Error fetching conflict analysis: {str(e)}")
            return None

    async def _analyze_single_conflict(
        self,
        conflict: Dict,
        relationship_id: str,
        partner_names: Dict[str, str],
        include_enrichment: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a single conflict (used for parallel processing).
        Returns result dict with status.
        """
        conflict_id = conflict["id"]

        try:
            # Get transcript
            transcript_data = db_service.get_conflict_transcript(conflict_id)

            if not transcript_data or not transcript_data.get("transcript_text"):
                return {"conflict_id": conflict_id, "status": "skipped", "reason": "no_transcript"}

            transcript = transcript_data["transcript_text"]

            # Run Gottman analysis
            await self.analyze_conflict(
                conflict_id=conflict_id,
                transcript=transcript,
                relationship_id=relationship_id,
                partner_a_name=partner_names.get("partner_a", "Partner A"),
                partner_b_name=partner_names.get("partner_b", "Partner B")
            )

            # Also run enrichment (trigger phrases, unmet needs) if requested
            if include_enrichment:
                try:
                    from app.services.conflict_enrichment_service import conflict_enrichment_service

                    previous_conflicts = db_service.get_previous_conflicts(relationship_id, limit=5)

                    enrichment = await conflict_enrichment_service.extract_conflict_relationships(
                        conflict_id=conflict_id,
                        transcript=transcript,
                        relationship_id=relationship_id,
                        previous_conflicts=previous_conflicts
                    )

                    await conflict_enrichment_service.save_trigger_phrases(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        phrases=enrichment.trigger_phrases
                    )

                    await conflict_enrichment_service.save_unmet_needs(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        needs=enrichment.unmet_needs
                    )

                    await conflict_enrichment_service.update_conflict_enrichment(
                        conflict_id=conflict_id,
                        enrichment=enrichment
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Enrichment failed for {conflict_id}: {str(e)}")

            return {"conflict_id": conflict_id, "status": "success"}

        except Exception as e:
            logger.error(f"❌ Failed to analyze {conflict_id}: {str(e)}")
            return {"conflict_id": conflict_id, "status": "failed", "error": str(e)}

    async def backfill_all_conflicts(
        self,
        relationship_id: str,
        batch_size: int = 10,
        include_enrichment: bool = True
    ) -> Dict[str, Any]:
        """
        Backfill Gottman analysis for all conflicts in a relationship.
        Runs in parallel batches for efficiency.

        Args:
            relationship_id: The relationship UUID
            batch_size: Number of conflicts to process in parallel (default 10)
            include_enrichment: Also backfill trigger phrases and unmet needs

        Returns:
            Results dict with counts
        """
        try:
            logger.info(f"🔄 Starting parallel backfill for relationship {relationship_id} (batch size: {batch_size})")

            # Get all conflicts
            conflicts = db_service.get_all_conflicts(relationship_id)

            if not conflicts:
                return {"total": 0, "analyzed": 0, "failed": 0, "skipped": 0}

            # Get partner names once (for all conflicts)
            partner_names = db_service.get_partner_names(relationship_id)

            results = {
                "total": len(conflicts),
                "analyzed": 0,
                "failed": 0,
                "skipped": 0
            }

            # Process in batches
            for batch_start in range(0, len(conflicts), batch_size):
                batch = conflicts[batch_start:batch_start + batch_size]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (len(conflicts) + batch_size - 1) // batch_size

                logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} conflicts)")

                # Run batch in parallel
                tasks = [
                    self._analyze_single_conflict(
                        conflict=c,
                        relationship_id=relationship_id,
                        partner_names=partner_names,
                        include_enrichment=include_enrichment
                    )
                    for c in batch
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count results
                for result in batch_results:
                    if isinstance(result, Exception):
                        results["failed"] += 1
                        logger.error(f"❌ Batch task exception: {str(result)}")
                    elif isinstance(result, dict):
                        if result.get("status") == "success":
                            results["analyzed"] += 1
                        elif result.get("status") == "skipped":
                            results["skipped"] += 1
                        else:
                            results["failed"] += 1

                logger.info(f"✅ Batch {batch_num} complete: {results['analyzed']} analyzed so far")

            logger.info(f"🏁 Backfill complete: {results}")
            return results

        except Exception as e:
            logger.error(f"❌ Backfill failed: {str(e)}")
            raise

    async def backfill_async_background(
        self,
        relationship_id: str,
        batch_size: int = 10
    ) -> None:
        """
        Run backfill completely in background (fire and forget).
        Used for automatic background processing.
        """
        try:
            logger.info(f"🔄 Starting background backfill for {relationship_id}")
            results = await self.backfill_all_conflicts(
                relationship_id=relationship_id,
                batch_size=batch_size,
                include_enrichment=True
            )
            logger.info(f"✅ Background backfill complete: {results}")
        except Exception as e:
            logger.error(f"❌ Background backfill failed: {str(e)}")


# Singleton instance
gottman_service = GottmanAnalysisService()
