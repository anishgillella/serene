import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_seeded_data():
    """Check what data was seeded in the database"""
    print("🔍 Checking seeded data...\n")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        
        # ==========================================
        # 1. Cycle Events
        # ==========================================
        print("=" * 60)
        print("📅 CYCLE EVENTS")
        print("=" * 60)
        cursor.execute("""
            SELECT event_type, event_date, notes, cycle_day, symptoms
            FROM cycle_events
            WHERE relationship_id = %s
            ORDER BY event_date DESC;
        """, (RELATIONSHIP_ID,))
        
        events = cursor.fetchall()
        if events:
            for event in events:
                print(f"  • {event['event_date']} - {event['event_type']}")
                print(f"    Notes: {event['notes']}")
                print(f"    Symptoms: {event['symptoms']}")
                print()
        else:
            print("  (No cycle events found)")
        
        # ==========================================
        # 2. Memorable Dates
        # ==========================================
        print("=" * 60)
        print("🎉 MEMORABLE DATES")
        print("=" * 60)
        cursor.execute("""
            SELECT event_type, title, description, event_date, partner_id
            FROM memorable_dates
            WHERE relationship_id = %s
            ORDER BY event_date;
        """, (RELATIONSHIP_ID,))
        
        dates = cursor.fetchall()
        if dates:
            for date in dates:
                print(f"  • {date['title']} ({date['event_type']})")
                print(f"    Date: {date['event_date']}")
                print(f"    Description: {date['description']}")
                print(f"    Partner: {date['partner_id']}")
                print()
        else:
            print("  (No memorable dates found)")
        
        # ==========================================
        # 3. Intimacy Events
        # ==========================================
        print("=" * 60)
        print("💕 INTIMACY EVENTS")
        print("=" * 60)
        cursor.execute("""
            SELECT timestamp, initiator_partner_id
            FROM intimacy_events
            WHERE relationship_id = %s
            ORDER BY timestamp DESC;
        """, (RELATIONSHIP_ID,))
        
        intimacy = cursor.fetchall()
        if intimacy:
            for event in intimacy:
                print(f"  • {event['timestamp']} - Initiated by {event['initiator_partner_id']}")
        else:
            print("  (No intimacy events found)")
        print()
        
        # ==========================================
        # 4. Conflicts & Rants
        # ==========================================
        print("=" * 60)
        print("💬 CONFLICTS & RANT MESSAGES")
        print("=" * 60)
        cursor.execute("""
            SELECT c.id, c.started_at, c.status,
                   COUNT(r.id) as rant_count
            FROM conflicts c
            LEFT JOIN rant_messages r ON c.id = r.conflict_id
            WHERE c.relationship_id = %s
            GROUP BY c.id, c.started_at, c.status
            ORDER BY c.started_at DESC;
        """, (RELATIONSHIP_ID,))
        
        conflicts = cursor.fetchall()
        if conflicts:
            for conflict in conflicts:
                print(f"  • Conflict {conflict['id'][:8]}...")
                print(f"    Started: {conflict['started_at']}")
                print(f"    Status: {conflict['status']}")
                print(f"    Rant messages: {conflict['rant_count']}")
                
                # Show rant messages
                cursor.execute("""
                    SELECT partner_id, content
                    FROM rant_messages
                    WHERE conflict_id = %s
                    ORDER BY created_at;
                """, (conflict['id'],))
                
                rants = cursor.fetchall()
                for rant in rants:
                    print(f"      - {rant['partner_id']}: {rant['content'][:60]}...")
                print()
        else:
            print("  (No conflicts found)")
        
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("✅ Data check complete!")
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")

if __name__ == "__main__":
    check_seeded_data()
