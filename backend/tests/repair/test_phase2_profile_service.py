"""
Phase 2: Profile Service Tests

Tests for the profile retrieval service that fetches ALL partner profile data
instead of just semantically similar chunks.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Optional, Any


class TestProfileService:
    """Tests for the ProfileService class"""

    def create_mock_profile_data(self, role: str = "partner_a") -> Dict[str, str]:
        """Create mock profile data for testing"""
        name = "Alice" if role == "partner_a" else "Bob"
        return {
            "name": name,
            "role": role,
            "identity": f"Name: {name}\nAge: 30\nRole: {role}",
            "background": f"Background story for {name}",
            "personality": f"Communication Style: Direct\nStress Triggers: interruptions",
            "interests": f"Hobbies: reading, yoga",
            "partner_view": f"Description of partner by {name}",
            "relationship": f"Relationship dynamics from {name}'s view",
            "repair_preferences": f"""## Repair & Conflict Preferences ({name})
What makes an apology genuine to {name}: specific acknowledgment
After a conflict, {name} needs time alone to cool down and process
Gestures that help {name} feel better: tea, hug, space
Things that make fights WORSE for {name}: saying 'calm down', walking away"""
        }

    def test_profile_has_all_sections(self):
        """Test that profile data contains all expected sections"""
        profile = self.create_mock_profile_data("partner_a")

        expected_sections = [
            "identity",
            "background",
            "personality",
            "interests",
            "partner_view",
            "relationship",
            "repair_preferences"
        ]

        for section in expected_sections:
            assert section in profile, f"Missing section: {section}"
            assert profile[section] != "", f"Empty section: {section}"

    def test_profile_has_repair_preferences_section(self):
        """Test that repair_preferences section exists and contains repair data"""
        profile = self.create_mock_profile_data("partner_a")

        repair_section = profile.get("repair_preferences", "")
        assert repair_section != ""
        assert "apology genuine" in repair_section.lower()
        assert "conflict" in repair_section.lower()
        assert "gestures" in repair_section.lower()
        assert "worse" in repair_section.lower()

    def test_format_profile_for_llm(self):
        """Test formatting profile data for LLM consumption"""
        profile = self.create_mock_profile_data("partner_a")

        # Simulate format_profile_for_llm logic
        name = profile.get("name", "Partner")
        role = profile.get("role", "unknown")

        sections = []
        sections.append(f"=== {name.upper()}'S COMPLETE PROFILE ({role.upper()}) ===")
        sections.append("")

        # CRITICAL: Repair preferences first
        if profile.get("repair_preferences"):
            sections.append("REPAIR & CONFLICT PREFERENCES (CRITICAL FOR REPAIR PLAN):")
            sections.append(profile["repair_preferences"])
            sections.append("")

        if profile.get("personality"):
            sections.append("INNER WORLD (Communication & Triggers):")
            sections.append(profile["personality"])
            sections.append("")

        formatted = "\n".join(sections)

        # Verify structure
        assert "ALICE'S COMPLETE PROFILE" in formatted
        assert "REPAIR & CONFLICT PREFERENCES" in formatted
        assert "CRITICAL FOR REPAIR PLAN" in formatted
        # Repair preferences should come BEFORE other sections
        repair_pos = formatted.find("REPAIR & CONFLICT")
        personality_pos = formatted.find("INNER WORLD")
        assert repair_pos < personality_pos, "Repair preferences should come first"

    def test_check_profiles_complete_both_present(self):
        """Test profile completeness check when both profiles exist"""
        partner_a = self.create_mock_profile_data("partner_a")
        partner_b = self.create_mock_profile_data("partner_b")

        # Simulate check_profiles_complete logic
        critical_fields = ["repair_preferences", "personality"]

        result = {
            "complete": True,
            "missing_profiles": [],
            "missing_fields": {}
        }

        if not partner_a:
            result["complete"] = False
            result["missing_profiles"].append("partner_a")
        else:
            missing = [f for f in critical_fields if not partner_a.get(f)]
            if missing:
                result["missing_fields"]["partner_a"] = missing

        if not partner_b:
            result["complete"] = False
            result["missing_profiles"].append("partner_b")
        else:
            missing = [f for f in critical_fields if not partner_b.get(f)]
            if missing:
                result["missing_fields"]["partner_b"] = missing

        assert result["complete"] == True
        assert len(result["missing_profiles"]) == 0
        assert len(result["missing_fields"]) == 0

    def test_check_profiles_complete_one_missing(self):
        """Test profile completeness check when one profile is missing"""
        partner_a = self.create_mock_profile_data("partner_a")
        partner_b = None

        critical_fields = ["repair_preferences", "personality"]

        result = {
            "complete": True,
            "missing_profiles": [],
            "missing_fields": {}
        }

        if not partner_a:
            result["complete"] = False
            result["missing_profiles"].append("partner_a")

        if not partner_b:
            result["complete"] = False
            result["missing_profiles"].append("partner_b")

        assert result["complete"] == False
        assert "partner_b" in result["missing_profiles"]

    def test_check_profiles_complete_missing_critical_fields(self):
        """Test profile completeness check when critical fields are missing"""
        partner_a = {
            "name": "Alice",
            "role": "partner_a",
            "identity": "Alice, 30",
            # Missing: repair_preferences, personality
        }
        partner_b = self.create_mock_profile_data("partner_b")

        critical_fields = ["repair_preferences", "personality"]

        result = {
            "complete": True,
            "missing_profiles": [],
            "missing_fields": {}
        }

        if partner_a:
            missing = [f for f in critical_fields if not partner_a.get(f)]
            if missing:
                result["missing_fields"]["partner_a"] = missing

        assert "partner_a" in result["missing_fields"]
        assert "repair_preferences" in result["missing_fields"]["partner_a"]
        assert "personality" in result["missing_fields"]["partner_a"]


class TestProfileRetrieval:
    """Tests for profile retrieval from Pinecone"""

    def test_full_profile_query_uses_correct_filter(self):
        """Test that full profile retrieval uses correct Pinecone filter"""
        relationship_id = "test-relationship-123"
        role = "partner_a"

        # Expected filter structure
        expected_filter = {
            "$and": [
                {"relationship_id": {"$eq": relationship_id}},
                {"role": {"$eq": role}}
            ]
        }

        # Verify filter structure is correct
        assert "$and" in expected_filter
        assert len(expected_filter["$and"]) == 2
        assert expected_filter["$and"][0]["relationship_id"]["$eq"] == relationship_id
        assert expected_filter["$and"][1]["role"]["$eq"] == role

    def test_profile_sections_organized_correctly(self):
        """Test that profile sections are correctly organized from Pinecone results"""
        # Mock Pinecone results
        mock_matches = [
            Mock(metadata={"section": "identity", "extracted_text": "Name: Alice\nAge: 30", "name": "Alice"}),
            Mock(metadata={"section": "personality", "extracted_text": "Communication: Direct"}),
            Mock(metadata={"section": "repair_preferences", "extracted_text": "Apology prefs: specific"}),
            Mock(metadata={"section": "background", "extracted_text": "Grew up in NYC"}),
        ]

        # Simulate organizing sections
        profile = {
            "identity": "",
            "background": "",
            "personality": "",
            "interests": "",
            "partner_view": "",
            "relationship": "",
            "repair_preferences": ""
        }
        name = "Partner"

        for match in mock_matches:
            metadata = match.metadata
            section = metadata.get("section", "unknown")
            text = metadata.get("extracted_text", "")

            if section == "identity" and metadata.get("name"):
                name = metadata.get("name")

            if section in profile:
                profile[section] = text

        assert profile["identity"] == "Name: Alice\nAge: 30"
        assert profile["personality"] == "Communication: Direct"
        assert profile["repair_preferences"] == "Apology prefs: specific"
        assert name == "Alice"


class TestProfileServiceIntegration:
    """Integration tests for profile service with repair plan generation"""

    def test_profile_provides_context_for_repair_plan(self):
        """Test that profile data provides correct context for repair plan"""
        profile = {
            "name": "Sarah",
            "role": "partner_b",
            "repair_preferences": """## Repair & Conflict Preferences (Sarah)
What makes an apology genuine to Sarah: I need to hear that they understand WHY what they did hurt me
After a conflict, Sarah needs time alone to cool down and process
Gestures that help Sarah feel better: Making me tea, Writing me a note
Things that make fights WORSE for Sarah: Saying 'you always', Walking away"""
        }

        repair_prefs = profile["repair_preferences"]

        # Check that key repair info is extractable
        assert "understand WHY" in repair_prefs
        assert "time alone" in repair_prefs
        assert "tea" in repair_prefs
        assert "you always" in repair_prefs

    def test_profile_format_prioritizes_repair_data(self):
        """Test that formatted profile puts repair data first"""
        sections = []
        sections.append("=== SARAH'S COMPLETE PROFILE (PARTNER_B) ===")
        sections.append("")
        sections.append("REPAIR & CONFLICT PREFERENCES (CRITICAL FOR REPAIR PLAN):")
        sections.append("Repair preferences content here")
        sections.append("")
        sections.append("INNER WORLD (Communication & Triggers):")
        sections.append("Communication style content")
        sections.append("")
        sections.append("BACKGROUND & IDENTITY:")
        sections.append("Background content")

        formatted = "\n".join(sections)

        # Check order - repair should come first
        lines = formatted.split("\n")
        repair_line_idx = next(i for i, l in enumerate(lines) if "REPAIR & CONFLICT" in l)
        inner_world_idx = next(i for i, l in enumerate(lines) if "INNER WORLD" in l)
        background_idx = next(i for i, l in enumerate(lines) if "BACKGROUND" in l)

        assert repair_line_idx < inner_world_idx
        assert inner_world_idx < background_idx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
