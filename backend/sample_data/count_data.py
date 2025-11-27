import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def count_entries():
    """Count entries in each table"""
    print("📊 Database Table Counts:\n")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        
        tables = [
            "cycle_events",
            "memorable_dates",
            "intimacy_events",
            "conflicts",
            "rant_messages"
        ]
        
        for table in tables:
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE relationship_id = %s;
            """ if table != "rant_messages" else f"""
                SELECT COUNT(*) FROM {table}
                WHERE conflict_id IN (SELECT id FROM conflicts WHERE relationship_id = %s);
            """, (RELATIONSHIP_ID,))
            
            count = cursor.fetchone()[0]
            print(f"   • {table.ljust(20)}: {count} entries")
            
        print("\n✅ Count check complete!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error counting data: {e}")

if __name__ == "__main__":
    count_entries()
