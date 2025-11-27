import os
import uuid
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def seed_data():
    """Seed the database with comprehensive knowledge base data"""
    print("🌱 Seeding knowledge base data...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Hardcoded IDs from the project
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        PARTNER_A_ID = "partner_a"  # Adrian
        PARTNER_B_ID = "partner_b"  # Elara
        
        today = datetime.now().date()
        
        # ==========================================
        # 1. Cycle Events (Elara) - 20+ entries (approx 2 years of history)
        # ==========================================
        print("   1. Seeding Cycle Events (20+ entries)...")
        cycle_events = []
        # Generate 24 months of cycle history
        current_date = today
        for i in range(24):
            # Approx 28 day cycle with some variation
            cycle_start = current_date - timedelta(days=28 * i)
            
            # Add period start
            cycle_events.append((RELATIONSHIP_ID, PARTNER_B_ID, "period_start", cycle_start, "Period started", 1, ["cramps", "fatigue"] if i % 3 == 0 else []))
            
            # Add ovulation (approx day 14)
            cycle_events.append((RELATIONSHIP_ID, PARTNER_B_ID, "ovulation", cycle_start + timedelta(days=14), "Ovulation likely", 14, ["high_energy"]))
            
            # Add PMS symptoms (approx day 25)
            cycle_events.append((RELATIONSHIP_ID, PARTNER_B_ID, "symptom_log", cycle_start + timedelta(days=25), "Feeling moody", 25, ["mood_swings", "bloating"]))

        for event in cycle_events:
            cursor.execute("""
                INSERT INTO cycle_events (relationship_id, partner_id, event_type, event_date, notes, cycle_day, symptoms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, event)

        # ==========================================
        # 2. Memorable Dates - 20+ entries
        # ==========================================
        print("   2. Seeding Memorable Dates (20+ entries)...")
        base_year = today.year
        memorable_dates = [
            # Recurring Annual Events (for this year and next)
            (RELATIONSHIP_ID, "anniversary", "First Date Anniversary", "The day we first met at the coffee shop", datetime(base_year, 12, 11).date(), True, 7, "#ec4899", None),
            (RELATIONSHIP_ID, "birthday", "Elara's Birthday", "Planning a surprise dinner", datetime(base_year + 1, 1, 11).date(), True, 14, "#8b5cf6", PARTNER_B_ID),
            (RELATIONSHIP_ID, "birthday", "Adrian's Birthday", "He wants a quiet day", datetime(base_year, 7, 30).date(), True, 14, "#3b82f6", PARTNER_A_ID),
            (RELATIONSHIP_ID, "anniversary", "Official Couple Anniversary", "When we made it official", datetime(base_year, 2, 14).date(), True, 7, "#ef4444", None),
            (RELATIONSHIP_ID, "milestone", "Moved in Together", "Anniversary of moving into the apartment", datetime(base_year, 5, 1).date(), True, 7, "#10b981", None),
            (RELATIONSHIP_ID, "milestone", "Got the Dog (Barkley)", "Barkley's Gotcha Day", datetime(base_year, 9, 15).date(), True, 3, "#f59e0b", None),
            
            # Holidays & Special Occasions
            (RELATIONSHIP_ID, "holiday", "Valentine's Day", "Dinner reservation needed", datetime(base_year + 1, 2, 14).date(), True, 14, "#ef4444", None),
            (RELATIONSHIP_ID, "holiday", "New Year's Eve", "Party at Mike's", datetime(base_year, 12, 31).date(), True, 7, "#6366f1", None),
            
            # One-time Events (Future & Past)
            (RELATIONSHIP_ID, "trip", "Trip to Italy", "Flight at 6pm", today + timedelta(days=60), False, 30, "#0ea5e9", None),
            (RELATIONSHIP_ID, "event", "Concert Tickets", "Coldplay Concert", today + timedelta(days=25), False, 1, "#8b5cf6", None),
            (RELATIONSHIP_ID, "appointment", "Couples Therapy", "Dr. Smith", today + timedelta(days=3), False, 1, "#14b8a6", None),
            (RELATIONSHIP_ID, "appointment", "Vet Appointment", "Barkley's checkup", today + timedelta(days=10), False, 1, "#f59e0b", None),
            (RELATIONSHIP_ID, "social", "Dinner with Parents", "Adrian's parents visiting", today + timedelta(days=8), False, 2, "#f43f5e", None),
            (RELATIONSHIP_ID, "social", "Sarah's Wedding", "Need to buy gift", today + timedelta(days=45), False, 7, "#ec4899", None),
            (RELATIONSHIP_ID, "work", "Adrian's Work Presentation", "Big deadline", today + timedelta(days=5), False, 1, "#64748b", PARTNER_A_ID),
            (RELATIONSHIP_ID, "work", "Elara's Gallery Opening", "Art show downtown", today + timedelta(days=20), False, 7, "#d946ef", PARTNER_B_ID),
            (RELATIONSHIP_ID, "trip", "Weekend Getaway", "Cabin in the woods", today + timedelta(days=90), False, 14, "#22c55e", None),
            (RELATIONSHIP_ID, "milestone", "Lease Renewal", "Need to sign papers", today + timedelta(days=120), False, 30, "#f97316", None),
            (RELATIONSHIP_ID, "event", "Cooking Class", "Italian cooking night", today - timedelta(days=10), False, 0, "#facc15", None), # Past event
            (RELATIONSHIP_ID, "event", "Wine Tasting", "Vineyard tour", today - timedelta(days=45), False, 0, "#881337", None), # Past event
        ]
        
        for date in memorable_dates:
            cursor.execute("""
                INSERT INTO memorable_dates (relationship_id, event_type, title, description, event_date, is_recurring, reminder_days, color_tag, partner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, date)

        # ==========================================
        # 3. Intimacy Events - 20+ entries
        # ==========================================
        print("   3. Seeding Intimacy Events (20+ entries)...")
        # Generate random intimacy events over the last 3 months
        import random
        for i in range(25):
            # Random date in the last 90 days
            days_ago = random.randint(1, 90)
            event_date = datetime.now() - timedelta(days=days_ago)
            
            # Random initiator
            initiator = PARTNER_A_ID if random.random() > 0.5 else PARTNER_B_ID
            
            cursor.execute("""
                INSERT INTO intimacy_events (relationship_id, timestamp, initiator_partner_id)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (RELATIONSHIP_ID, event_date, initiator))

        # ==========================================
        # 4. Conflicts & Rant Messages (Multiple scenarios)
        # ==========================================
        print("   4. Seeding Conflicts & Rants...")
        
        # Rant scenarios with realistic back-and-forth (20+ scenarios, 8+ messages each)
        conflict_scenarios = [
            # 1. Phone usage during quality time
            {
                "started_at": datetime.now() - timedelta(hours=2),
                "status": "active",
                "rants": [
                    (PARTNER_A_ID, "user", "I feel like she never listens to me when I talk about my work. I was trying to tell her about the new project launch."),
                    (PARTNER_B_ID, "user", "He's always on his phone during dinner, it drives me crazy. I was checking an urgent email for two seconds."),
                    (PARTNER_A_ID, "user", "It wasn't two seconds, Elara. You were scrolling for five minutes while I was mid-sentence."),
                    (PARTNER_B_ID, "user", "Oh please, like you don't check sports scores when I'm talking about my day?"),
                    (PARTNER_A_ID, "user", "I do that maybe once a week. You do this every single night. It feels disrespectful."),
                    (PARTNER_B_ID, "user", "I have a demanding job! I can't just disconnect completely like you can."),
                    (PARTNER_A_ID, "user", "So my job isn't demanding? I make time for us. Why can't you?"),
                    (PARTNER_B_ID, "user", "I do make time! But when I'm stressed, I need to stay on top of things or I get anxious."),
                ]
            },
            # 2. Forgot anniversary
            {
                "started_at": datetime.now() - timedelta(days=1),
                "status": "active",
                "rants": [
                    (PARTNER_A_ID, "user", "I can't believe you forgot our anniversary dinner reservation. I had been planning this for weeks."),
                    (PARTNER_B_ID, "user", "He acts like I did it on purpose. I've been so stressed with work deadlines, things just slipped my mind."),
                    (PARTNER_A_ID, "user", "This isn't the first time. Last month you forgot my birthday too. It feels like I'm not a priority."),
                    (PARTNER_B_ID, "user", "That's not fair. I apologized for the birthday thing and made it up to you. Why does he keep bringing up the past?"),
                    (PARTNER_A_ID, "user", "Because it's a pattern! You prioritize everything else over our milestones."),
                    (PARTNER_B_ID, "user", "I literally worked until midnight all week to clear my schedule for tonight! I just forgot to call the restaurant."),
                    (PARTNER_A_ID, "user", "It's not just the restaurant. It's the fact that I have to remind you of every single important date."),
                    (PARTNER_B_ID, "user", "I'm trying my best, Adrian! I'm not perfect. Can't we just order takeout and have a nice night in?"),
                ]
            },
            # 3. Communication style clash
            {
                "started_at": datetime.now() - timedelta(days=3),
                "status": "active",
                "rants": [
                    (PARTNER_A_ID, "user", "Every time I try to talk about something serious, she shuts down and goes quiet. How am I supposed to fix things if we can't even talk?"),
                    (PARTNER_B_ID, "user", "He doesn't understand that I need time to process my feelings. He wants answers immediately and it overwhelms me."),
                    (PARTNER_A_ID, "user", "I'm not asking for immediate answers. I just want to know she's listening and cares about how I feel."),
                    (PARTNER_B_ID, "user", "I do care! But the way he approaches conversations feels like an interrogation, not a discussion."),
                    (PARTNER_A_ID, "user", "I ask questions because you don't offer any information! I'm trying to pull teeth here."),
                    (PARTNER_B_ID, "user", "See? That's what I mean. You get aggressive and loud, and it makes me want to retreat."),
                    (PARTNER_A_ID, "user", "I'm loud because I'm frustrated! I feel like I'm talking to a brick wall."),
                    (PARTNER_B_ID, "user", "And I feel like I'm being attacked. If you could just lower your voice and give me space, I'd talk."),
                ]
            },
            # 4. Household chores
            {
                "started_at": datetime.now() - timedelta(days=5),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "I'm tired of being the only one who cleans the apartment. He leaves dishes in the sink for days."),
                    (PARTNER_A_ID, "user", "She acts like I never help, but I do the laundry and take out the trash. Why doesn't that count?"),
                    (PARTNER_B_ID, "user", "Because I have to remind you every single time! I shouldn't have to be your manager."),
                    (PARTNER_A_ID, "user", "Maybe if she didn't have such high standards for everything, I'd feel like my efforts are actually appreciated."),
                    (PARTNER_B_ID, "user", "High standards? I just want a sink that doesn't smell like rotting food!"),
                    (PARTNER_A_ID, "user", "I was going to do them after the game. You just couldn't wait five minutes."),
                    (PARTNER_B_ID, "user", "It wasn't five minutes, it was three days! We have ants now because of you."),
                    (PARTNER_A_ID, "user", "Okay, fine. I'll do the dishes right now. Are you happy?"),
                ]
            },
            # 5. Social plans conflict
            {
                "started_at": datetime.now() - timedelta(days=7),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She made plans with her friends on the one night I asked her to keep free for us. It's like her friends always come first."),
                    (PARTNER_B_ID, "user", "He told me about it last minute! I had already committed to my friends weeks ago. He expects me to drop everything."),
                    (PARTNER_A_ID, "user", "I mentioned it a month ago, but she probably wasn't listening like usual."),
                    (PARTNER_B_ID, "user", "That's such a lie. He mentioned 'maybe doing something' but never confirmed actual plans. Now he's gaslighting me."),
                    (PARTNER_A_ID, "user", "I am not gaslighting you. I explicitly said 'Keep Friday the 15th open for the concert'."),
                    (PARTNER_B_ID, "user", "You said 'I might buy tickets'. You never said you actually bought them!"),
                    (PARTNER_A_ID, "user", "I wanted to surprise you! But clearly, a night out with Sarah is more important."),
                    (PARTNER_B_ID, "user", "Don't bring Sarah into this. You know I haven't seen her in months."),
                ]
            },
            # 6. Money spending disagreement
            {
                "started_at": datetime.now() - timedelta(days=9),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She spent $300 on art supplies without even discussing it with me. We're supposed to be saving for a trip."),
                    (PARTNER_B_ID, "user", "It's my money from my freelance work! He acts like I need his permission to buy things for my career."),
                    (PARTNER_A_ID, "user", "It's not about permission, it's about being a team and making decisions together."),
                    (PARTNER_B_ID, "user", "I earned that extra money specifically for this. It didn't come out of our joint account."),
                    (PARTNER_A_ID, "user", "But we agreed to put all extra income towards the house down payment."),
                    (PARTNER_B_ID, "user", "You bought that expensive gaming monitor last month! Was that for the house?"),
                    (PARTNER_A_ID, "user", "That was a birthday gift from my parents! I didn't spend our savings."),
                    (PARTNER_B_ID, "user", "Well, this is an investment in my sanity. Painting helps me relax."),
                ]
            },
            # 7. Family visit tension
            {
                "started_at": datetime.now() - timedelta(days=12),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "His mom made passive-aggressive comments about my cooking the entire visit and he said nothing."),
                    (PARTNER_A_ID, "user", "She's being overly sensitive. My mom was just trying to be helpful with suggestions."),
                    (PARTNER_B_ID, "user", "Helpful? She literally said 'In our family, we season our food properly.' That's not helpful, that's insulting."),
                    (PARTNER_A_ID, "user", "She didn't mean it like that. You know she has no filter."),
                    (PARTNER_B_ID, "user", "That's no excuse! You should have defended me. You just sat there eating."),
                    (PARTNER_A_ID, "user", "If I say something, she gets upset and cries. I just wanted a peaceful dinner."),
                    (PARTNER_B_ID, "user", "So my feelings matter less than your mom's tantrums?"),
                    (PARTNER_A_ID, "user", "No, but you're an adult. You can handle a few comments. She's old."),
                ]
            },
            # 8. Late night work calls
            {
                "started_at": datetime.now() - timedelta(days=14),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He took a work call at 11 PM when we were in the middle of watching our show together."),
                    (PARTNER_A_ID, "user", "It was my boss! What was I supposed to do, ignore it?"),
                    (PARTNER_B_ID, "user", "You could have told him you'd call back in 10 minutes. Our time together matters too."),
                    (PARTNER_A_ID, "user", "This project is critical, Elara. If I mess up, I could lose my bonus."),
                    (PARTNER_B_ID, "user", "There's always a 'critical project'. Last month it was the merger. Before that, the audit."),
                    (PARTNER_A_ID, "user", "I'm working hard for our future! Why can't you support that?"),
                    (PARTNER_B_ID, "user", "I do support you. But I also want a husband who is present, not married to his phone."),
                    (PARTNER_A_ID, "user", "It was one call. You're blowing this out of proportion."),
                ]
            },
            # 9. Gym time vs couple time
            {
                "started_at": datetime.now() - timedelta(days=16),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She goes to the gym every single evening. We barely spend time together anymore."),
                    (PARTNER_B_ID, "user", "So I'm supposed to give up my health and fitness routine because he wants to watch TV together?"),
                    (PARTNER_A_ID, "user", "I'm not asking you to give it up, just maybe go in the morning sometimes so we can have evenings together."),
                    (PARTNER_B_ID, "user", "I am not a morning person. You know this. I can't lift weights at 6 AM."),
                    (PARTNER_A_ID, "user", "Then maybe skip one day? Or go on weekends? I miss you, Elara."),
                    (PARTNER_B_ID, "user", "I miss you too, but the gym is my stress relief. If I don't go, I'm cranky."),
                    (PARTNER_A_ID, "user", "You're cranky anyway because you're exhausted from working out all the time!"),
                    (PARTNER_B_ID, "user", "Wow. Thanks for the support. Maybe you should join me instead of complaining."),
                ]
            },
            # 10. Vacation planning disagreement
            {
                "started_at": datetime.now() - timedelta(days=18),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He wants to go camping for our vacation. I've told him a hundred times I hate camping."),
                    (PARTNER_A_ID, "user", "And I've told her I don't want to spend our savings on an expensive resort. We need to compromise."),
                    (PARTNER_B_ID, "user", "Compromise means meeting in the middle, not me doing something I absolutely hate."),
                    (PARTNER_A_ID, "user", "It's glamping! There's a bed and a bathroom. It's not sleeping on the ground."),
                    (PARTNER_B_ID, "user", "It's still bugs and dirt and no room service. I want to relax, not work."),
                    (PARTNER_A_ID, "user", "We can relax by the fire! It's romantic."),
                    (PARTNER_B_ID, "user", "My idea of romantic is a beach and a cocktail, not a tent and a bear."),
                    (PARTNER_A_ID, "user", "Fine. We'll go to the beach. But we're staying at a budget hotel, not the Ritz."),
                ]
            },
            # 11. Pet care responsibilities
            {
                "started_at": datetime.now() - timedelta(days=20),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "I'm the only one who ever walks the dog. She wanted a pet but I'm doing all the work."),
                    (PARTNER_B_ID, "user", "I feed him every morning and take him to the vet! Walking isn't the only responsibility."),
                    (PARTNER_A_ID, "user", "Walking is the hardest part! Especially when it's raining or freezing outside."),
                    (PARTNER_B_ID, "user", "I took him out yesterday morning! You were still asleep."),
                    (PARTNER_A_ID, "user", "Once. You took him out once. I've done it every night for two weeks."),
                    (PARTNER_B_ID, "user", "I'm exhausted after work! My feet hurt."),
                    (PARTNER_A_ID, "user", "My feet hurt too. We agreed to split this 50/50."),
                    (PARTNER_B_ID, "user", "Okay, I'll try to do more evening walks. Just stop keeping score."),
                ]
            },
            # 12. Sleep schedule conflict
            {
                "started_at": datetime.now() - timedelta(days=22),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He stays up until 2 AM gaming with his friends and then complains he's tired all day."),
                    (PARTNER_A_ID, "user", "It's the only time I get to relax and do something I enjoy. She goes to bed at 9 PM like a grandma."),
                    (PARTNER_B_ID, "user", "And then you wake me up stumbling into bed at 2 AM. It's disrespectful."),
                    (PARTNER_A_ID, "user", "I try to be quiet! You're just a light sleeper."),
                    (PARTNER_B_ID, "user", "You dropped your controller on the floor last night! It sounded like a gunshot."),
                    (PARTNER_A_ID, "user", "That was an accident. I said sorry."),
                    (PARTNER_B_ID, "user", "Sorry doesn't help me get back to sleep. I have to be up at 6."),
                    (PARTNER_A_ID, "user", "Maybe you should get earplugs. I need my downtime."),
                ]
            },
            # 13. Career opportunity discussion
            {
                "started_at": datetime.now() - timedelta(days=25),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "I got offered a promotion but it means relocating. She shot it down immediately without even discussing it."),
                    (PARTNER_B_ID, "user", "Because I just started my dream job here! Why is his career more important than mine?"),
                    (PARTNER_A_ID, "user", "I never said it was more important. I just wanted us to talk about it as a possibility."),
                    (PARTNER_B_ID, "user", "There's nothing to talk about. I'm not moving. End of story."),
                    (PARTNER_A_ID, "user", "That's incredibly selfish. This could double my salary."),
                    (PARTNER_B_ID, "user", "And it would end my career! I can't do my job remotely."),
                    (PARTNER_A_ID, "user", "We could find you something else. You're talented."),
                    (PARTNER_B_ID, "user", "I don't want 'something else'. I want this job. Why do I always have to sacrifice?"),
                ]
            },
            # 14. Social media oversharing
            {
                "started_at": datetime.now() - timedelta(days=27),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She posts everything about our relationship on Instagram. Can't we have some privacy?"),
                    (PARTNER_B_ID, "user", "It's my social media! If he's embarrassed to be seen with me, that's a different problem."),
                    (PARTNER_A_ID, "user", "I'm not embarrassed! I just don't want your 500 followers knowing we had a fight."),
                    (PARTNER_B_ID, "user", "I didn't post about the fight! I posted a quote about 'difficult times'."),
                    (PARTNER_A_ID, "user", "Which everyone knows is about me. My sister called me asking if we broke up."),
                    (PARTNER_B_ID, "user", "That's her problem for being nosy. It's my page, I can express myself."),
                    (PARTNER_A_ID, "user", "Not when it involves me. It's immature."),
                    (PARTNER_B_ID, "user", "You call it immature, I call it being authentic. I'm not going to hide my life."),
                ]
            },
            # 15. Ex-partner friendship
            {
                "started_at": datetime.now() - timedelta(days=30),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He's still friends with his ex on social media and they comment on each other's posts. It makes me uncomfortable."),
                    (PARTNER_A_ID, "user", "We dated for 2 months in college, 5 years ago. She's in a serious relationship now. This is ridiculous."),
                    (PARTNER_B_ID, "user", "Then why does it bother you so much to just unfollow her? If it's not a big deal, why fight about it?"),
                    (PARTNER_A_ID, "user", "Because you're being controlling! I shouldn't have to cut off friends because you're insecure."),
                    (PARTNER_B_ID, "user", "It's not insecurity, it's boundaries. She posted a heart emoji on your selfie."),
                    (PARTNER_A_ID, "user", "She posts hearts on everyone's photos! It means nothing."),
                    (PARTNER_B_ID, "user", "It means something to me. It feels disrespectful to our relationship."),
                    (PARTNER_A_ID, "user", "Fine. I'll mute her. But I'm not blocking her just to appease your jealousy."),
                ]
            },
            # 16. Cooking preferences
            {
                "started_at": datetime.now() - timedelta(days=32),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She cooks vegetarian meals all the time. I'm not vegetarian and I'm tired of pretending tofu is a steak."),
                    (PARTNER_B_ID, "user", "I'm doing all the cooking! If he wants meat, he can cook it himself."),
                    (PARTNER_A_ID, "user", "I get home late! You know I can't cook at 8 PM."),
                    (PARTNER_B_ID, "user", "And I don't want to handle raw meat. It grosses me out."),
                    (PARTNER_A_ID, "user", "So I'm forced to be vegetarian? That's not fair."),
                    (PARTNER_B_ID, "user", "You can buy a rotisserie chicken! Or order takeout. I'm not stopping you."),
                    (PARTNER_A_ID, "user", "I want a home-cooked meal that I actually enjoy."),
                    (PARTNER_B_ID, "user", "Then learn to cook on weekends and meal prep. I'm not your personal chef."),
                ]
            },
            # 17. Temperature wars
            {
                "started_at": datetime.now() - timedelta(days=35),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He keeps the apartment at 65 degrees. I'm freezing all the time and he tells me to wear a sweater."),
                    (PARTNER_A_ID, "user", "And she wants it at 75! I'm sweating. It's easier to add layers than to cool down."),
                    (PARTNER_B_ID, "user", "I can't wear gloves inside! My hands are ice blocks."),
                    (PARTNER_A_ID, "user", "75 is a sauna. I can't sleep when it's that hot."),
                    (PARTNER_B_ID, "user", "Can we compromise at 70?"),
                    (PARTNER_A_ID, "user", "68. That's standard room temperature."),
                    (PARTNER_B_ID, "user", "68 is still cold for me! Why do you get to dictate the comfort level?"),
                    (PARTNER_A_ID, "user", "Because I pay the electric bill, and heating is expensive."),
                ]
            },
            # 18. Movie/TV show choices
            {
                "started_at": datetime.now() - timedelta(days=37),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "We always watch what she wants. I suggested an action movie and she rolled her eyes."),
                    (PARTNER_B_ID, "user", "Because the last 'action movie' he picked was 3 hours of explosions with no plot."),
                    (PARTNER_A_ID, "user", "It was a classic! You just didn't give it a chance."),
                    (PARTNER_B_ID, "user", "I fell asleep because it was boring. I like character-driven stories."),
                    (PARTNER_A_ID, "user", "So we have to watch depressing dramas every night? I want to be entertained."),
                    (PARTNER_B_ID, "user", "We watched your sci-fi show last week!"),
                    (PARTNER_A_ID, "user", "One episode. Then you complained about the aliens looking fake."),
                    (PARTNER_B_ID, "user", "They did look fake! Okay, you pick tonight. No complaints. I promise."),
                ]
            },
            # 19. Gift giving expectations
            {
                "started_at": datetime.now() - timedelta(days=40),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "He got me a blender for my birthday. A BLENDER. Like I'm some 1950s housewife."),
                    (PARTNER_A_ID, "user", "She literally said she wanted a high-powered blender for smoothies! I was listening!"),
                    (PARTNER_B_ID, "user", "For Christmas, not my birthday! Birthdays are supposed to be romantic, not practical."),
                    (PARTNER_A_ID, "user", "It was a $400 Vitamix! That's a nice gift."),
                    (PARTNER_B_ID, "user", "It's a kitchen appliance. It says 'make me food'."),
                    (PARTNER_A_ID, "user", "It says 'I support your healthy lifestyle'. You're reading too much into it."),
                    (PARTNER_B_ID, "user", "I wanted jewelry or a weekend away. Something for *me*, not the house."),
                    (PARTNER_A_ID, "user", "Okay, I get it. No appliances. I'll return it."),
                ]
            },
            # 20. Weekend plans spontaneity
            {
                "started_at": datetime.now() - timedelta(days=42),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She needs to plan everything weeks in advance. I suggested a spontaneous road trip and she freaked out."),
                    (PARTNER_B_ID, "user", "Because I had plans! I like knowing what my weekend looks like. That's not freaking out, that's being organized."),
                    (PARTNER_A_ID, "user", "You had plans to 'clean the closet'. That can wait."),
                    (PARTNER_B_ID, "user", "It's been on my list for a month! I need to get it done."),
                    (PARTNER_A_ID, "user", "You're so rigid. Where's your sense of adventure?"),
                    (PARTNER_B_ID, "user", "My adventure requires an itinerary. I don't like driving aimlessly."),
                    (PARTNER_A_ID, "user", "That's the fun of it! Discovering new places."),
                    (PARTNER_B_ID, "user", "That's the stress of it! Wondering where we'll sleep. Next time, give me 3 days notice."),
                ]
            },
            # 21. Snoring complaints
            {
                "started_at": datetime.now() - timedelta(days=45),
                "status": "completed",
                "rants": [
                    (PARTNER_B_ID, "user", "His snoring is so loud I can't sleep. I've asked him to see a doctor and he refuses."),
                    (PARTNER_A_ID, "user", "I don't snore that badly. She's exaggerating. Maybe she's just a light sleeper."),
                    (PARTNER_B_ID, "user", "I recorded you! Listen to this. It sounds like a chainsaw."),
                    (PARTNER_A_ID, "user", "Okay, that was one bad night. I had a cold."),
                    (PARTNER_B_ID, "user", "It's every night! I'm moving to the couch if you don't make an appointment."),
                    (PARTNER_A_ID, "user", "Fine, I'll go. But don't blame me if they say I'm fine."),
                    (PARTNER_B_ID, "user", "They won't. You stop breathing sometimes. It's scary."),
                    (PARTNER_A_ID, "user", "Wait, really? Why didn't you say that part?"),
                ]
            },
            # 22. Bathroom time monopoly
            {
                "started_at": datetime.now() - timedelta(days=48),
                "status": "completed",
                "rants": [
                    (PARTNER_A_ID, "user", "She takes 45-minute showers every morning. I'm always late for work because I can't get ready."),
                    (PARTNER_B_ID, "user", "Then wake up earlier! I'm not going to rush my morning routine because he hits snooze 5 times."),
                    (PARTNER_A_ID, "user", "We have one bathroom! You can't hog it for an hour."),
                    (PARTNER_B_ID, "user", "It's my self-care time. It's the only peace I get."),
                    (PARTNER_A_ID, "user", "Can't you shower at night?"),
                    (PARTNER_B_ID, "user", "My hair gets greasy if I sleep on it wet. You know this."),
                    (PARTNER_A_ID, "user", "Then I'm showering first. I'll be in and out in 10 minutes."),
                    (PARTNER_B_ID, "user", "Fine. But if you use all the hot water, you're dead."),
                ]
            },
        ]
        
        for scenario in conflict_scenarios:
            # Create conflict
            conflict_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO conflicts (id, relationship_id, started_at, status)
                VALUES (%s, %s, %s, %s);
            """, (conflict_id, RELATIONSHIP_ID, scenario["started_at"], scenario["status"]))
            
            # Add rant messages with incrementing timestamps to ensure order
            current_msg_time = scenario["started_at"]
            for partner_id, role, content in scenario["rants"]:
                # Increment time by 1 minute for each message
                current_msg_time += timedelta(minutes=1)
                
                cursor.execute("""
                    INSERT INTO rant_messages (conflict_id, partner_id, role, content, created_at)
                    VALUES (%s, %s, %s, %s, %s);
                """, (conflict_id, partner_id, role, content, current_msg_time))
        
        print(f"      Created {len(conflict_scenarios)} conflicts with rant messages")

            
        conn.commit()
        print("✅ Knowledge base seeded successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")

if __name__ == "__main__":
    seed_data()
