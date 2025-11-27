import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def clean_database():
    """Delete all data from the database tables"""
    print("🧹 Cleaning database...\n")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        
        # Tables with relationship_id
        tables_with_relationship = [
            ("cycle_events", "Cycle events"),
            ("memorable_dates", "Memorable dates"),
            ("intimacy_events", "Intimacy events"),
            ("profiles", "Profiles"),
            ("conflict_analysis", "Conflict analysis"),
            ("repair_plans", "Repair plans"),
            ("conflicts", "Conflicts"),
        ]
        
        # Tables without relationship_id (delete via conflict_id)
        print("   Deleting messages linked to conflicts...")
        cursor.execute("""
            DELETE FROM rant_messages
            WHERE conflict_id IN (
                SELECT id FROM conflicts WHERE relationship_id = %s
            );
        """, (RELATIONSHIP_ID,))
        print(f"   ✅ Deleted {cursor.rowcount} Rant messages")
        
        cursor.execute("""
            DELETE FROM mediator_messages
            WHERE session_id IN (
                SELECT id FROM mediator_sessions 
                WHERE conflict_id IN (
                    SELECT id FROM conflicts WHERE relationship_id = %s
                )
            );
        """, (RELATIONSHIP_ID,))
        print(f"   ✅ Deleted {cursor.rowcount} Mediator messages")
        
        cursor.execute("""
            DELETE FROM mediator_sessions
            WHERE conflict_id IN (
                SELECT id FROM conflicts WHERE relationship_id = %s
            );
        """, (RELATIONSHIP_ID,))
        print(f"   ✅ Deleted {cursor.rowcount} Mediator sessions")
        
        # Delete tables with relationship_id
        for table, description in tables_with_relationship:
            cursor.execute(f"""
                DELETE FROM {table}
                WHERE relationship_id = %s;
            """, (RELATIONSHIP_ID,))
            deleted = cursor.rowcount
            print(f"   ✅ Deleted {deleted} {description}")
        
        conn.commit()
        print("\n✅ Database cleaned successfully!\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error cleaning database: {e}")
        raise

if __name__ == "__main__":
    clean_database()
