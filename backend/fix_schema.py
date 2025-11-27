import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")

DATABASE_URL = os.getenv("DATABASE_URL")

def fix_schema():
    print(f"Connecting to {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Drop the table if it exists
        print("Dropping mediator_messages table...")
        cursor.execute("DROP TABLE IF EXISTS mediator_messages;")
        
        # Recreate it with correct schema
        print("Recreating mediator_messages table...")
        cursor.execute("""
            CREATE TABLE mediator_messages (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id UUID REFERENCES mediator_sessions(id) ON DELETE CASCADE,
                content JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT uq_mediator_messages_session_id UNIQUE (session_id)
            );
        """)
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mediator_messages_session ON mediator_messages(session_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mediator_messages_updated_at ON mediator_messages(updated_at DESC);")
        
        # Enable RLS
        print("Enabling RLS...")
        cursor.execute("ALTER TABLE mediator_messages ENABLE ROW LEVEL SECURITY;")
        cursor.execute("CREATE POLICY \"Allow public access to mediator_messages\" ON mediator_messages FOR ALL USING (true);")
        
        conn.commit()
        print("✅ Schema fixed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_schema()
