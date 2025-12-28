"""
Profile Retrieval Service for Personalized Repair Plans (Phase 2)

Fetches ALL profile data for a partner, not just semantically similar chunks.
This ensures repair plans have access to all repair-relevant information.
"""
import logging
from typing import Optional, Dict, List, Any, Literal
from app.services.pinecone_service import pinecone_service

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for fetching complete partner profiles for repair plan personalization"""

    def __init__(self):
        self.pinecone = pinecone_service
        logger.info("✅ Initialized Profile Service for full profile retrieval")

    async def get_full_partner_profile(
        self,
        relationship_id: str,
        role: Literal["partner_a", "partner_b"]
    ) -> Optional[Dict[str, str]]:
        """
        Fetch ALL profile chunks for a partner, not just semantically similar ones.
        Returns structured profile data ready for LLM consumption.

        Args:
            relationship_id: The relationship UUID
            role: 'partner_a' or 'partner_b'

        Returns:
            Dictionary with sections: identity, background, personality, interests,
            partner_view, relationship, repair_preferences
        """
        try:
            if not self.pinecone.index:
                logger.warning("⚠️ Pinecone index not initialized")
                return None

            # Fetch all chunks for this partner from the profiles namespace
            # We use a dummy vector and high top_k with filter to get all chunks
            results = self.pinecone.index.query(
                vector=[0.0] * 1024,  # Dummy vector (dimension 1024)
                top_k=100,  # Get all possible chunks
                namespace="profiles",
                include_metadata=True,
                filter={
                    "$and": [
                        {"relationship_id": {"$eq": relationship_id}},
                        {"role": {"$eq": role}}
                    ]
                }
            )

            if not results or not results.matches:
                logger.warning(f"⚠️ No profile found for {role} in relationship {relationship_id}")
                return None

            # Organize by section
            profile = {
                "identity": "",
                "background": "",
                "personality": "",
                "interests": "",
                "partner_view": "",
                "relationship": "",
                "repair_preferences": "",
                "reconnection": ""  # NEW: Phase 2
            }

            name = "Partner"  # Default name

            for match in results.matches:
                metadata = match.metadata
                section = metadata.get("section", "unknown")
                text = metadata.get("extracted_text", "") or metadata.get("text", "")

                # Extract name from identity section
                if section == "identity" and metadata.get("name"):
                    name = metadata.get("name")

                if section in profile:
                    profile[section] = text
                elif section == "inner_world":
                    # Map inner_world to personality for consistency
                    profile["personality"] = text

            logger.info(f"✅ Retrieved full profile for {name} ({role})")

            # Add name to profile
            profile["name"] = name
            profile["role"] = role

            return profile

        except Exception as e:
            logger.error(f"❌ Error fetching full profile for {role}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def get_both_partner_profiles(
        self,
        relationship_id: str
    ) -> Dict[str, Optional[Dict[str, str]]]:
        """
        Fetch profiles for both partners in a relationship.

        Returns:
            Dictionary with 'partner_a' and 'partner_b' profiles
        """
        partner_a = await self.get_full_partner_profile(relationship_id, "partner_a")
        partner_b = await self.get_full_partner_profile(relationship_id, "partner_b")

        return {
            "partner_a": partner_a,
            "partner_b": partner_b
        }

    def format_profile_for_llm(
        self,
        profile: Optional[Dict[str, str]],
        partner_name: Optional[str] = None
    ) -> str:
        """
        Format profile sections into LLM-ready text.
        Prioritizes repair-relevant information.

        Args:
            profile: Profile dictionary from get_full_partner_profile
            partner_name: Override name if provided

        Returns:
            Formatted string for LLM prompt injection
        """
        if not profile:
            return "Profile not available"

        name = partner_name or profile.get("name", "Partner")
        role = profile.get("role", "unknown")

        # Build formatted output prioritizing repair-relevant data
        sections = []

        sections.append(f"=== {name.upper()}'S COMPLETE PROFILE ({role.upper()}) ===")
        sections.append("")

        # CRITICAL: Repair preferences first
        if profile.get("repair_preferences"):
            sections.append("REPAIR & CONFLICT PREFERENCES (CRITICAL FOR REPAIR PLAN):")
            sections.append(profile["repair_preferences"])
            sections.append("")

        # Reconnection preferences (also critical for repair)
        if profile.get("reconnection"):
            sections.append("RECONNECTION & LOVE (HOW THEY COME BACK TOGETHER):")
            sections.append(profile["reconnection"])
            sections.append("")

        # Inner world / personality (communication style, triggers)
        if profile.get("personality"):
            sections.append("INNER WORLD (Communication & Triggers):")
            sections.append(profile["personality"])
            sections.append("")

        # View on partner
        if profile.get("partner_view"):
            sections.append("VIEW ON PARTNER:")
            sections.append(profile["partner_view"])
            sections.append("")

        # Background & identity
        if profile.get("identity") or profile.get("background"):
            sections.append("BACKGROUND & IDENTITY:")
            if profile.get("identity"):
                sections.append(profile["identity"])
            if profile.get("background"):
                sections.append(profile["background"])
            sections.append("")

        # Relationship dynamics
        if profile.get("relationship"):
            sections.append("RELATIONSHIP DYNAMICS:")
            sections.append(profile["relationship"])
            sections.append("")

        # Interests (lower priority for repair plans)
        if profile.get("interests"):
            sections.append("INTERESTS:")
            sections.append(profile["interests"])
            sections.append("")

        return "\n".join(sections)

    def check_profiles_complete(
        self,
        partner_a_profile: Optional[Dict[str, str]],
        partner_b_profile: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Check if both partner profiles are complete enough for personalized repair plans.

        Returns:
            Dictionary with:
            - complete: bool
            - missing_profiles: List of missing profile roles
            - missing_fields: Dict of role -> list of missing critical fields
        """
        critical_fields = ["repair_preferences", "personality"]

        result = {
            "complete": True,
            "missing_profiles": [],
            "missing_fields": {}
        }

        if not partner_a_profile:
            result["complete"] = False
            result["missing_profiles"].append("partner_a")
        else:
            missing = [f for f in critical_fields if not partner_a_profile.get(f)]
            if missing:
                result["missing_fields"]["partner_a"] = missing

        if not partner_b_profile:
            result["complete"] = False
            result["missing_profiles"].append("partner_b")
        else:
            missing = [f for f in critical_fields if not partner_b_profile.get(f)]
            if missing:
                result["missing_fields"]["partner_b"] = missing

        return result


# Singleton instance
profile_service = ProfileService()
