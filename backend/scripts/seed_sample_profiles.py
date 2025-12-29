"""
Seed Sample Profiles for Adrian and Elara

This script inserts fully-formed sample profiles through the proper onboarding flow:
1. Creates DB records in the profiles table
2. Uploads JSON to S3
3. Embeds and upserts to Pinecone

Run from backend directory:
    python -m scripts.seed_sample_profiles
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.onboarding import OnboardingSubmission, PartnerProfile, RelationshipProfile, process_onboarding_task
import uuid
from app.services.db_service import db_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Profile: Adrian (Partner A) - The Pursuer
ADRIAN_PROFILE = PartnerProfile(
    name="Adrian",
    role="partner_a",
    age=32,
    communication_style="Direct and logical. I prefer to address issues head-on rather than let them fester. Sometimes I can come across as intense when I'm trying to solve a problem, but I genuinely want to find solutions together.",
    stress_triggers=["Being ignored or getting the silent treatment", "Feeling like my concerns aren't being taken seriously", "Ambiguity and uncertainty about where we stand", "When conversations get postponed indefinitely"],
    soothing_mechanisms=["Going for a run to clear my head", "Making lists and action plans", "Talking through problems out loud", "Cooking a complex meal that requires focus"],
    background_story="I grew up in a household where my parents never argued in front of us - they'd just go silent for days. I never learned what healthy conflict looked like, so I've worked hard to be someone who addresses things directly. I have a successful career as a software architect, which sometimes means I approach relationship problems like engineering problems - looking for logical solutions when sometimes my partner just wants to be heard.",
    hobbies=["Long-distance running", "Building mechanical keyboards", "Reading sci-fi novels", "Cooking elaborate weekend brunches"],
    favorite_food="A perfectly cooked medium-rare ribeye",
    favorite_cuisine="Japanese (especially omakase)",
    favorite_sports=["Running", "Rock climbing"],
    favorite_books=["Dune", "The Three-Body Problem", "Thinking, Fast and Slow", "Attached by Amir Levine"],
    favorite_celebrities=["Neil deGrasse Tyson", "Brené Brown"],
    traumatic_experiences="My parents' cold, silent conflicts left me with a deep fear of being shut out. When Elara withdraws, it triggers that childhood feeling of walking on eggshells, never knowing what was wrong.",
    key_life_experiences="Traveling solo through Japan for a month taught me that I can be okay alone, but it also showed me how much richer experiences are when shared. Meeting Elara at that coffee shop in Seattle felt like finding someone who saw the world the way I did.",
    partner_description="Elara is incredibly creative and empathetic - she sees nuances in situations that I completely miss. She has this way of making ordinary moments feel magical. She's also deeply sensitive, which is beautiful but sometimes means she needs space to process things that I want to solve immediately.",
    what_i_admire="Her emotional intelligence, her artistic eye, how she remembers every small detail about the people she loves, and her ability to find joy in simple moments.",
    what_frustrates_me="When she withdraws and won't tell me what's wrong. I end up feeling like I'm chasing her, which makes her retreat more. It's a cycle we keep falling into.",
    apology_preferences="I need to understand the 'why' - what happened and what we'll do differently. A genuine acknowledgment of impact matters more than just saying sorry.",
    post_conflict_need="connection",
    repair_gestures=["Having a calm debrief about what happened", "Making a plan together for next time", "Physical affection once we've talked it through"],
    escalation_triggers=["Stonewalling or the silent treatment", "Dismissive responses like 'whatever' or 'fine'", "Bringing up past resolved issues"],
    relationship_duration="3 years",
    how_you_met="We met at a coffee shop in Seattle. She was sketching in a notebook and I accidentally knocked over her latte reaching for a napkin. I insisted on buying her a new one, and we ended up talking for four hours.",
    love_language="words",
    conflict_role="pursue",
    happiest_memory="Our trip to Iceland. Watching the Northern Lights together, wrapped in blankets in the middle of nowhere. She cried at how beautiful it was, and I cried watching her.",
    biggest_fear="That one day she'll withdraw and not come back. That I'll push too hard and lose her.",
    time_to_reconnect="minutes",
    reconnection_activities=["Talking it through", "Going for a walk together", "Cooking a meal together"],
    what_makes_you_feel_loved=["When she initiates conversation about her feelings", "Random texts saying she's thinking of me", "When she chooses to spend time with me over being alone"],
    how_you_know_resolved="When we can talk about what happened calmly and she's affectionate again. When she voluntarily shares what was going on for her.",
    off_limit_topics=["Her past relationship with Marco", "My workaholic tendencies during the first year"]
)

ADRIAN_RELATIONSHIP = RelationshipProfile(
    recurring_arguments=["How much time Adrian spends working vs. quality time together", "Adrian pushing to talk when Elara needs space", "Different approaches to handling stress and conflict", "Planning vs. spontaneity in daily life"],
    shared_goals=["Buy a house with a garden in the next 2 years", "Travel to at least one new country each year", "Build a relationship where we both feel secure enough to be vulnerable", "Eventually have children when we've worked through our communication patterns"],
    relationship_dynamic="Pursuer-Withdrawer pattern. Adrian tends to seek connection and resolution during conflicts, while Elara often needs space first. This creates a dance where Adrian's pursuit can feel overwhelming to Elara, and her withdrawal feels like rejection to Adrian. They're working on meeting in the middle."
)

# Sample Profile: Elara (Partner B) - The Withdrawer
ELARA_PROFILE = PartnerProfile(
    name="Elara",
    role="partner_b",
    age=29,
    communication_style="Reflective and emotional. I need time to process my feelings before I can articulate them. When I'm overwhelmed, I tend to go quiet - not because I'm punishing anyone, but because I genuinely don't have words yet.",
    stress_triggers=["Feeling pressured to talk before I'm ready", "Raised voices or intense energy", "Being told how I 'should' feel", "Feeling like I'm being analyzed or fixed"],
    soothing_mechanisms=["Taking a long bath with music", "Journaling to process my thoughts", "Creating art - painting or sketching", "Being in nature, especially near water"],
    background_story="I'm a freelance illustrator who grew up in a chaotic household where emotions ran high. Yelling was common, and I learned to protect myself by going to my room and disappearing into my art. It's still my sanctuary. I've been in therapy for two years working on understanding that conflict doesn't have to be scary, and that withdrawing isn't always the answer.",
    hobbies=["Watercolor painting", "Pottery", "Hiking in forests", "Collecting vintage books", "Practicing yoga"],
    favorite_food="My grandmother's homemade pasta",
    favorite_cuisine="Italian (authentic, not Americanized)",
    favorite_sports=["Yoga", "Swimming"],
    favorite_books=["The Secret Garden", "Norwegian Wood by Murakami", "Big Magic by Elizabeth Gilbert", "The Body Keeps the Score"],
    favorite_celebrities=["Florence Welch", "Hayao Miyazaki"],
    traumatic_experiences="Growing up with a volatile father who would explode over small things. I never knew what would set him off, so I became hypervigilant to emotional shifts. Any sign of frustration in a partner makes my nervous system go into protection mode.",
    key_life_experiences="Living abroad in Portugal for a year in my mid-twenties. It taught me I could rebuild my life anywhere, and that solitude can be healing. But it also showed me I don't want to be alone forever. Meeting Adrian showed me what it could feel like to be with someone who actually wants to understand me.",
    partner_description="Adrian is brilliant and devoted - when he loves, he loves with his whole self. He's more logical than me, which can be grounding but sometimes frustrating. He wants to fix everything immediately, and I wish he'd just sit with me sometimes instead of jumping to solutions.",
    what_i_admire="His consistency. He shows up every single day. His intelligence, his ambition, the way he makes me laugh with his terrible puns, and how safe I feel with him even when we're struggling.",
    what_frustrates_me="When he won't give me space to breathe during a disagreement. He follows me from room to room wanting to 'resolve it now' when I just need 20 minutes to collect myself. It makes me want to run further away.",
    apology_preferences="I need to feel like my partner truly gets how I felt, not just that they're sorry it happened. Genuine empathy and a soft tone mean everything to me.",
    post_conflict_need="space",
    repair_gestures=["Giving me time, then coming back gently", "A handwritten note or soft text", "Making me tea without asking", "Physical comfort once I'm ready - a long hug"],
    escalation_triggers=["Being followed when I'm trying to take space", "Logical arguments when I'm emotional", "Feeling like a problem to be solved", "Rehashing the same points repeatedly"],
    relationship_duration="3 years",
    how_you_met="Adrian knocked over my latte at a coffee shop where I was sketching. He was so flustered and genuine - nothing like the overly confident guys I'd dated before. We talked for hours and I remember thinking, 'This one sees me.'",
    love_language="time",
    conflict_role="withdraw",
    happiest_memory="Iceland, under the Northern Lights. I felt so small and so held at the same time. Adrian didn't try to explain the science or take photos - he just held me while I cried at the beauty of it.",
    biggest_fear="That I'll shut down too many times and Adrian will give up on me. That my need for space will be seen as not loving him enough.",
    time_to_reconnect="hours",
    reconnection_activities=["Parallel time - being together but doing our own things", "A gentle walk in nature", "Watching a comfort movie together", "Him just holding my hand without talking"],
    what_makes_you_feel_loved=["When he gives me space without seeming angry about it", "Small acts of service like making me coffee", "When he remembers tiny details I mentioned weeks ago", "Slow, unhurried quality time"],
    how_you_know_resolved="When I feel soft toward him again. When the tightness in my chest releases and I want to be near him. When I can look at him without feeling defensive.",
    off_limit_topics=["My father's behavior", "The time I almost left during our first year"]
)

ELARA_RELATIONSHIP = RelationshipProfile(
    recurring_arguments=["Adrian pushing to resolve things when I need space", "Me withdrawing instead of communicating what I need", "Balancing social time (he wants more) vs. alone time (I need more)", "How to handle visits with my difficult family"],
    shared_goals=["Build a home that feels like a sanctuary for both of us", "Learn to fight in a way that brings us closer instead of creating distance", "Support each other's careers while prioritizing our relationship", "Create new family traditions that are healthier than what we grew up with"],
    relationship_dynamic="We're a classic pursuer-withdrawer couple trying to break the pattern. When conflict hits, Adrian wants to talk and I want space. His pursuit feels like pressure, my withdrawal feels like rejection. We're learning: I try to say 'I need 30 minutes, then I'll come back' instead of just disappearing. He tries to give me that time without following up every 5 minutes."
)

RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"


async def seed_profiles():
    """Seed both partner profiles into the system."""

    # Create Adrian's submission
    adrian_submission = OnboardingSubmission(
        relationship_id=RELATIONSHIP_ID,
        partner_id="partner_a",
        partner_profile=ADRIAN_PROFILE,
        relationship_profile=ADRIAN_RELATIONSHIP
    )

    # Create Elara's submission
    elara_submission = OnboardingSubmission(
        relationship_id=RELATIONSHIP_ID,
        partner_id="partner_b",
        partner_profile=ELARA_PROFILE,
        relationship_profile=ELARA_RELATIONSHIP
    )

    # Process Adrian
    logger.info("=" * 50)
    logger.info("🚀 Seeding Adrian's profile (partner_a)...")
    logger.info("=" * 50)

    adrian_pdf_id = str(uuid.uuid4())

    # Create DB record first
    try:
        db_service.create_profile(
            relationship_id=RELATIONSHIP_ID,
            pdf_type="onboarding_profile",
            partner_id="partner_a",
            filename="onboarding_questionnaire.json",
            file_path="",
            pdf_id=adrian_pdf_id,
            extracted_text_length=0
        )
        logger.info(f"✅ Created DB record for Adrian: {adrian_pdf_id}")
    except Exception as e:
        logger.warning(f"DB record may already exist: {e}")

    # Process (uploads to S3 + Pinecone)
    await process_onboarding_task(adrian_submission, adrian_pdf_id)
    logger.info("✅ Adrian's profile seeded successfully!")

    # Process Elara
    logger.info("=" * 50)
    logger.info("🚀 Seeding Elara's profile (partner_b)...")
    logger.info("=" * 50)

    elara_pdf_id = str(uuid.uuid4())

    # Create DB record first
    try:
        db_service.create_profile(
            relationship_id=RELATIONSHIP_ID,
            pdf_type="onboarding_profile",
            partner_id="partner_b",
            filename="onboarding_questionnaire.json",
            file_path="",
            pdf_id=elara_pdf_id,
            extracted_text_length=0
        )
        logger.info(f"✅ Created DB record for Elara: {elara_pdf_id}")
    except Exception as e:
        logger.warning(f"DB record may already exist: {e}")

    # Process (uploads to S3 + Pinecone)
    await process_onboarding_task(elara_submission, elara_pdf_id)
    logger.info("✅ Elara's profile seeded successfully!")

    logger.info("=" * 50)
    logger.info("🎉 All sample profiles seeded! You can now view them in the Profile section.")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_profiles())
