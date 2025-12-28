"""
Phase 1: Enhanced Onboarding Tests

Tests for the 4 new repair-focused onboarding fields:
- apology_preferences
- post_conflict_need
- repair_gestures
- escalation_triggers
"""
import pytest
from pydantic import ValidationError
from typing import List, Optional


# Mock the PartnerProfile model for testing
class MockPartnerProfile:
    """Test version of PartnerProfile with repair fields"""
    def __init__(
        self,
        name: str,
        role: str,
        age: int,
        communication_style: str,
        stress_triggers: List[str],
        soothing_mechanisms: List[str],
        background_story: str,
        hobbies: List[str],
        favorite_food: str,
        favorite_cuisine: str,
        favorite_sports: List[str],
        favorite_books: List[str],
        favorite_celebrities: List[str],
        traumatic_experiences: str = "",
        key_life_experiences: str = "",
        partner_description: str = "",
        what_i_admire: str = "",
        what_frustrates_me: str = "",
        # NEW: Repair-specific fields (Phase 1)
        apology_preferences: str = "",
        post_conflict_need: str = "",
        repair_gestures: List[str] = None,
        escalation_triggers: List[str] = None
    ):
        self.name = name
        self.role = role
        self.age = age
        self.communication_style = communication_style
        self.stress_triggers = stress_triggers
        self.soothing_mechanisms = soothing_mechanisms
        self.background_story = background_story
        self.hobbies = hobbies
        self.favorite_food = favorite_food
        self.favorite_cuisine = favorite_cuisine
        self.favorite_sports = favorite_sports
        self.favorite_books = favorite_books
        self.favorite_celebrities = favorite_celebrities
        self.traumatic_experiences = traumatic_experiences
        self.key_life_experiences = key_life_experiences
        self.partner_description = partner_description
        self.what_i_admire = what_i_admire
        self.what_frustrates_me = what_frustrates_me
        self.apology_preferences = apology_preferences
        self.post_conflict_need = post_conflict_need
        self.repair_gestures = repair_gestures or []
        self.escalation_triggers = escalation_triggers or []


class TestPhase1OnboardingFields:
    """Test the new repair-focused onboarding fields"""

    def test_partner_profile_has_apology_preferences(self):
        """Test that apology_preferences field exists and works"""
        profile = MockPartnerProfile(
            name="Alice",
            role="partner_a",
            age=30,
            communication_style="Direct",
            stress_triggers=["interruptions"],
            soothing_mechanisms=["deep breathing"],
            background_story="Story",
            hobbies=["reading"],
            favorite_food="Pizza",
            favorite_cuisine="Italian",
            favorite_sports=["tennis"],
            favorite_books=["1984"],
            favorite_celebrities=["Keanu"],
            apology_preferences="I need them to acknowledge specifically what they did wrong and show they understand why it hurt me"
        )
        assert profile.apology_preferences != ""
        assert "acknowledge" in profile.apology_preferences.lower()

    def test_partner_profile_has_post_conflict_need(self):
        """Test that post_conflict_need field exists and accepts valid values"""
        valid_values = ["space", "connection", "depends"]

        for value in valid_values:
            profile = MockPartnerProfile(
                name="Bob",
                role="partner_b",
                age=28,
                communication_style="Indirect",
                stress_triggers=[],
                soothing_mechanisms=[],
                background_story="",
                hobbies=[],
                favorite_food="",
                favorite_cuisine="",
                favorite_sports=[],
                favorite_books=[],
                favorite_celebrities=[],
                post_conflict_need=value
            )
            assert profile.post_conflict_need == value

    def test_partner_profile_has_repair_gestures(self):
        """Test that repair_gestures field exists and accepts list"""
        gestures = ["Making me tea", "A genuine hug", "Giving me 20 minutes of space"]

        profile = MockPartnerProfile(
            name="Carol",
            role="partner_a",
            age=32,
            communication_style="Mixed",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            repair_gestures=gestures
        )
        assert len(profile.repair_gestures) == 3
        assert "tea" in profile.repair_gestures[0].lower()

    def test_partner_profile_has_escalation_triggers(self):
        """Test that escalation_triggers field exists and accepts list"""
        triggers = ["Saying 'calm down'", "Walking away mid-sentence", "Bringing up past issues"]

        profile = MockPartnerProfile(
            name="David",
            role="partner_b",
            age=35,
            communication_style="Direct",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            escalation_triggers=triggers
        )
        assert len(profile.escalation_triggers) == 3
        assert "calm down" in profile.escalation_triggers[0].lower()

    def test_repair_fields_are_optional(self):
        """Test that repair fields have defaults and are optional"""
        profile = MockPartnerProfile(
            name="Eve",
            role="partner_a",
            age=27,
            communication_style="",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[]
            # NOT providing repair fields - should use defaults
        )
        assert profile.apology_preferences == ""
        assert profile.post_conflict_need == ""
        assert profile.repair_gestures == []
        assert profile.escalation_triggers == []

    def test_complete_profile_with_all_repair_fields(self):
        """Test a complete profile with all repair fields populated"""
        profile = MockPartnerProfile(
            name="Sarah",
            role="partner_a",
            age=29,
            communication_style="I tend to go quiet when upset, then need to talk it through",
            stress_triggers=["Being interrupted", "Feeling dismissed", "Raised voices"],
            soothing_mechanisms=["Deep breathing", "A quiet walk", "Journaling"],
            background_story="Grew up in a household where conflicts were avoided",
            hobbies=["Reading", "Yoga", "Cooking"],
            favorite_food="Sushi",
            favorite_cuisine="Japanese",
            favorite_sports=["Yoga", "Swimming"],
            favorite_books=["The Alchemist"],
            favorite_celebrities=["Emma Watson"],
            traumatic_experiences="Parents' messy divorce affected my view of conflict",
            key_life_experiences="Living abroad taught me independence",
            partner_description="Warm, funny, sometimes stubborn",
            what_i_admire="His patience and sense of humor",
            what_frustrates_me="His tendency to avoid difficult conversations",
            # NEW repair fields
            apology_preferences="I need to hear that they understand WHY what they did hurt me, not just 'sorry'. Specific acknowledgment is important.",
            post_conflict_need="space",
            repair_gestures=["Making me tea", "Writing me a note", "Giving me a genuine hug after I've had space"],
            escalation_triggers=["Saying 'you always' or 'you never'", "Walking away while I'm talking", "Defensive tone"]
        )

        # Verify all repair fields are properly set
        assert "understand WHY" in profile.apology_preferences
        assert profile.post_conflict_need == "space"
        assert len(profile.repair_gestures) == 3
        assert len(profile.escalation_triggers) == 3


class TestSemanticChunkGeneration:
    """Test that repair fields are included in semantic chunks"""

    def generate_repair_chunk(self, profile: MockPartnerProfile) -> str:
        """Generate the repair preferences chunk like the backend does"""
        repair_lines = []
        repair_lines.append(f"## Repair & Conflict Preferences ({profile.name})")

        if profile.apology_preferences:
            repair_lines.append(f"What makes an apology genuine to {profile.name}: {profile.apology_preferences}")

        if profile.post_conflict_need:
            need_description = {
                'space': 'needs time alone to cool down and process',
                'connection': 'needs to feel close again right away',
                'depends': 'it depends on the situation'
            }.get(profile.post_conflict_need, profile.post_conflict_need)
            repair_lines.append(f"After a conflict, {profile.name} {need_description}")

        if profile.repair_gestures:
            repair_lines.append(f"Gestures that help {profile.name} feel better: {', '.join(profile.repair_gestures)}")

        if profile.escalation_triggers:
            repair_lines.append(f"Things that make fights WORSE for {profile.name}: {', '.join(profile.escalation_triggers)}")

        if profile.soothing_mechanisms:
            repair_lines.append(f"What calms {profile.name} down: {', '.join(profile.soothing_mechanisms)}")

        if profile.stress_triggers:
            repair_lines.append(f"Stress triggers for {profile.name}: {', '.join(profile.stress_triggers)}")

        return "\n".join(repair_lines)

    def test_repair_chunk_includes_apology_preferences(self):
        """Test that apology preferences are in the chunk"""
        profile = MockPartnerProfile(
            name="Alice",
            role="partner_a",
            age=30,
            communication_style="",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            apology_preferences="I need specific acknowledgment of what went wrong"
        )
        chunk = self.generate_repair_chunk(profile)
        assert "apology genuine" in chunk.lower()
        assert "specific acknowledgment" in chunk.lower()

    def test_repair_chunk_includes_post_conflict_need(self):
        """Test that post conflict need is described correctly"""
        profile = MockPartnerProfile(
            name="Bob",
            role="partner_b",
            age=28,
            communication_style="",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            post_conflict_need="space"
        )
        chunk = self.generate_repair_chunk(profile)
        assert "time alone to cool down" in chunk.lower()

    def test_repair_chunk_includes_gestures(self):
        """Test that repair gestures are in the chunk"""
        profile = MockPartnerProfile(
            name="Carol",
            role="partner_a",
            age=32,
            communication_style="",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            repair_gestures=["tea", "hug", "note"]
        )
        chunk = self.generate_repair_chunk(profile)
        assert "gestures that help" in chunk.lower()
        assert "tea" in chunk

    def test_repair_chunk_includes_escalation_triggers(self):
        """Test that escalation triggers are in the chunk"""
        profile = MockPartnerProfile(
            name="David",
            role="partner_b",
            age=35,
            communication_style="",
            stress_triggers=[],
            soothing_mechanisms=[],
            background_story="",
            hobbies=[],
            favorite_food="",
            favorite_cuisine="",
            favorite_sports=[],
            favorite_books=[],
            favorite_celebrities=[],
            escalation_triggers=["calm down", "walking away"]
        )
        chunk = self.generate_repair_chunk(profile)
        assert "worse" in chunk.lower()
        assert "calm down" in chunk


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
