import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def add_rant_messages():
    """Add rant messages to existing empty conflicts"""
    print("💬 Adding rant messages to existing conflicts...\n")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        PARTNER_A_ID = "partner_a"  # Adrian
        PARTNER_B_ID = "partner_b"  # Elara
        
        # Get conflicts with no rant messages
        cursor.execute("""
            SELECT c.id, c.started_at
            FROM conflicts c
            LEFT JOIN rant_messages r ON c.id = r.conflict_id
            WHERE c.relationship_id = %s
            GROUP BY c.id, c.started_at
            HAVING COUNT(r.id) = 0
            ORDER BY c.started_at DESC
            LIMIT 4;
        """, (RELATIONSHIP_ID,))
        
        empty_conflicts = cursor.fetchall()
        
        if not empty_conflicts:
            print("✅ No empty conflicts found!")
            return
        
        print(f"Found {len(empty_conflicts)} conflicts without rant messages\n")
        
        # Realistic rant scenarios
        rant_scenarios = [
            # Scenario 1: Forgot important date
            [
                (PARTNER_A_ID, "user", "I can't believe you forgot our anniversary dinner reservation. I had been planning this for weeks."),
                (PARTNER_B_ID, "user", "He acts like I did it on purpose. I've been so stressed with work deadlines, things just slipped my mind."),
                (PARTNER_A_ID, "user", "This isn't the first time. Last month you forgot my birthday too. It feels like I'm not a priority."),
                (PARTNER_B_ID, "user", "That's not fair. I apologized for the birthday thing and made it up to you. Why does he keep bringing up the past?"),
            ],
            # Scenario 2: Communication style clash
            [
                (PARTNER_A_ID, "user", "Every time I try to talk about something serious, she shuts down and goes quiet. How am I supposed to fix things if we can't even talk?"),
                (PARTNER_B_ID, "user", "He doesn't understand that I need time to process my feelings. He wants answers immediately and it overwhelms me."),
                (PARTNER_A_ID, "user", "I'm not asking for immediate answers. I just want to know she's listening and cares about how I feel."),
                (PARTNER_B_ID, "user", "I do care! But the way he approaches conversations feels like an interrogation, not a discussion."),
            ],
            # Scenario 3: Household responsibilities
            [
                (PARTNER_B_ID, "user", "I'm tired of being the only one who cleans the apartment. He leaves dishes in the sink for days."),
                (PARTNER_A_ID, "user", "She acts like I never help, but I do the laundry and take out the trash. Why doesn't that count?"),
                (PARTNER_B_ID, "user", "Because I have to remind you every single time! I shouldn't have to be your manager."),
                (PARTNER_A_ID, "user", "Maybe if she didn't have such high standards for everything, I'd feel like my efforts are actually appreciated."),
            ],
            # Scenario 4: Social plans conflict
            [
                (PARTNER_A_ID, "user", "She made plans with her friends on the one night I asked her to keep free for us. It's like her friends always come first."),
                (PARTNER_B_ID, "user", "He told me about it last minute! I had already committed to my friends weeks ago. He expects me to drop everything."),
                (PARTNER_A_ID, "user", "I mentioned it a month ago, but she probably wasn't listening like usual."),
                (PARTNER_B_ID, "user", "That's such a lie. He mentioned 'maybe doing something' but never confirmed actual plans. Now he's gaslighting me."),
            ],
        ]
        
        # Add rants to each empty conflict
        for idx, conflict in enumerate(empty_conflicts):
            if idx >= len(rant_scenarios):
                break
                
            conflict_id = conflict['id']
            scenario = rant_scenarios[idx]
            
            print(f"Adding {len(scenario)} rants to conflict {conflict_id[:8]}...")
            
            for partner_id, role, content in scenario:
                cursor.execute("""
                    INSERT INTO rant_messages (conflict_id, partner_id, role, content)
                    VALUES (%s, %s, %s, %s);
                """, (conflict_id, partner_id, role, content))
            
            print(f"  ✅ Added scenario {idx + 1}\n")
        
        conn.commit()
        print("✅ All rant messages added successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error adding rants: {e}")

if __name__ == "__main__":
    add_rant_messages()
