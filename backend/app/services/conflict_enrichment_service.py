"""
Conflict Enrichment Service - Phase 1
Captures trigger phrases, conflict linkages, and unmet needs
"""
import asyncio
import logging
import json
import re
from typing import List
from app.models.schemas import (
    TriggerPhrase,
    UnmetNeed,
    ConflictEnrichment,
)
from app.services.llm_service import llm_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class ConflictEnrichmentService:
    """Service for enriching conflicts with trigger analysis and relationship data"""

    async def extract_conflict_relationships(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        previous_conflicts: List[dict] = None,
    ) -> ConflictEnrichment:
        """
        Use LLM to identify:
        - Related past conflicts
        - Trigger phrases
        - Unmet needs
        - Resentment level

        Args:
            conflict_id: Current conflict ID
            transcript: Full transcript text
            relationship_id: Relationship ID
            previous_conflicts: List of previous conflicts for context

        Returns:
            ConflictEnrichment with structured analysis
        """
        try:
            logger.info(f"🔗 Enriching conflict {conflict_id} with relationship data")

            # Build context of previous conflicts
            conflict_history = ""
            if previous_conflicts:
                for conflict in previous_conflicts[-5:]:  # last 5 conflicts
                    topic = conflict.get("metadata", {}).get("topic", "Unknown")
                    conflict_history += f"- {conflict.get('started_at')}: {topic}\n"

            # Build enrichment prompt
            enrichment_prompt = self._build_enrichment_prompt(
                transcript, conflict_history
            )

            # Call LLM for analysis
            response_text = await asyncio.to_thread(
                llm_service.analyze_with_prompt, enrichment_prompt
            )

            # Parse response
            enrichment_data = self._parse_enrichment_response(response_text)

            # Create enrichment object
            enrichment = ConflictEnrichment(
                conflict_id=conflict_id,
                parent_conflict_id=enrichment_data.get("parent_conflict_id"),
                trigger_phrases=enrichment_data.get("trigger_phrases", []),
                unmet_needs=enrichment_data.get("unmet_needs", []),
                resentment_level=enrichment_data.get("resentment_level", 5),
                has_past_references=enrichment_data.get("has_past_references", False),
                is_continuation=enrichment_data.get("is_continuation", False),
            )

            logger.info(
                f"✅ Enrichment complete for conflict {conflict_id}: "
                f"{len(enrichment.trigger_phrases)} phrases, "
                f"{len(enrichment.unmet_needs)} needs, "
                f"resentment: {enrichment.resentment_level}/10"
            )

            return enrichment

        except Exception as e:
            logger.error(f"❌ Error enriching conflict {conflict_id}: {str(e)}")
            raise

    def _build_enrichment_prompt(self, transcript: str, conflict_history: str) -> str:
        """Build the enrichment analysis prompt"""

        prompt = f"""Analyze this conflict transcript for patterns and relationships:

CURRENT CONFLICT TRANSCRIPT:
{transcript[:2000]}... [truncated for analysis]

PREVIOUS CONFLICTS (last 5):
{conflict_history if conflict_history else "No previous conflicts"}

Please provide analysis in JSON format with these exact keys:

{{
  "parent_conflict_id": "uuid or null if not related to previous conflict",
  "is_continuation": true/false,
  "trigger_phrases": [
    {{
      "phrase": "exact quote from transcript",
      "phrase_category": "temporal_reference|passive_aggressive|blame|dismissal|threat|accusation",
      "emotional_intensity": 1-10,
      "references_past": true/false,
      "speaker": "partner_a|partner_b",
      "is_escalation_trigger": true/false
    }}
  ],
  "unmet_needs": [
    {{
      "need": "feeling_heard|trust|appreciation|respect|autonomy|security|intimacy|validation",
      "confidence": 0.0-1.0,
      "speaker": "partner_a|partner_b|both",
      "evidence": "supporting quote"
    }}
  ],
  "resentment_level": 1-10,
  "has_past_references": true/false
}}

Focus on:
1. Explicit temporal references ("yesterday", "last time", "you never")
2. Phrases that bring up past failures
3. Passive-aggressive statements showing stored resentment
4. Core unmet needs beneath surface complaints
5. Overall emotional intensity (resentment level)

Return ONLY valid JSON, no other text."""

        return prompt

    def _parse_enrichment_response(self, response_text: str) -> dict:
        """Parse LLM response into enrichment data"""
        try:
            # Try to find JSON block
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if not json_match:
                logger.warning("No JSON found in enrichment response, returning defaults")
                return self._default_enrichment()

            json_str = json_match.group()
            data = json.loads(json_str)

            # Convert response data to our models
            trigger_phrases = [
                TriggerPhrase(**phrase) for phrase in data.get("trigger_phrases", [])
            ]

            unmet_needs = [
                UnmetNeed(**need) for need in data.get("unmet_needs", [])
            ]

            return {
                "parent_conflict_id": data.get("parent_conflict_id"),
                "is_continuation": data.get("is_continuation", False),
                "trigger_phrases": trigger_phrases,
                "unmet_needs": unmet_needs,
                "resentment_level": data.get("resentment_level", 5),
                "has_past_references": data.get("has_past_references", False),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse enrichment JSON: {str(e)}")
            return self._default_enrichment()

    def _default_enrichment(self) -> dict:
        """Return default enrichment data"""
        return {
            "parent_conflict_id": None,
            "is_continuation": False,
            "trigger_phrases": [],
            "unmet_needs": [],
            "resentment_level": 5,
            "has_past_references": False,
        }

    async def save_trigger_phrases(
        self, conflict_id: str, relationship_id: str, phrases: List[TriggerPhrase]
    ) -> None:
        """Save trigger phrases to database"""
        try:
            for phrase in phrases:
                # db_service.save_trigger_phrase is sync, wrap in thread
                await asyncio.to_thread(
                    db_service.save_trigger_phrase,
                    relationship_id=relationship_id,
                    conflict_id=conflict_id,
                    phrase_data=phrase.dict(),
                )
            logger.info(f"Saved {len(phrases)} trigger phrases for conflict {conflict_id}")
        except Exception as e:
            logger.error(f"Error saving trigger phrases: {str(e)}")
            raise

    async def save_unmet_needs(
        self, conflict_id: str, relationship_id: str, needs: List[UnmetNeed]
    ) -> None:
        """Save unmet needs to database"""
        try:
            for need in needs:
                # db_service.save_unmet_need is sync, wrap in thread
                await asyncio.to_thread(
                    db_service.save_unmet_need,
                    relationship_id=relationship_id,
                    conflict_id=conflict_id,
                    need_data=need.dict(),
                )
            logger.info(f"Saved {len(needs)} unmet needs for conflict {conflict_id}")
        except Exception as e:
            logger.error(f"Error saving unmet needs: {str(e)}")
            raise

    async def update_conflict_enrichment(
        self, conflict_id: str, enrichment: ConflictEnrichment
    ) -> None:
        """Update conflict with enrichment data"""
        try:
            # db_service.update_conflict is sync, wrap in thread
            await asyncio.to_thread(
                db_service.update_conflict,
                conflict_id=conflict_id,
                parent_conflict_id=enrichment.parent_conflict_id,
                resentment_level=enrichment.resentment_level,
                has_past_references=enrichment.has_past_references,
                is_continuation=enrichment.is_continuation,
                unmet_needs=[n.need for n in enrichment.unmet_needs],
            )
            logger.info(f"Updated conflict enrichment for {conflict_id}")
        except Exception as e:
            logger.error(f"Error updating conflict enrichment: {str(e)}")
            raise


# Singleton instance
conflict_enrichment_service = ConflictEnrichmentService()
