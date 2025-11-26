#!/usr/bin/env python3
"""
Run the mediator messages migration script.
This will DROP and RECREATE the mediator_messages and mediator_sessions tables.

WARNING: This will delete all existing mediator conversation data!
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
import psycopg2

def run_migration():
    """Execute the migration script"""
    
    # Read the migration SQL file
    migration_file = Path(__file__).parent / "update_mediator_messages.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("=" * 70)
    print("⚠️  MEDIATOR MESSAGES MIGRATION")
    print("=" * 70)
    print("\nThis will:")
    print("  1. DROP the existing mediator_messages table (and all data)")
    print("  2. DROP the existing mediator_sessions table (and all data)")
    print("  3. CREATE new tables with updated schema")
    print("\n⚠️  WARNING: ALL EXISTING MEDIATOR CONVERSATION DATA WILL BE LOST!")
    print("=" * 70)
    
    # Get user confirmation
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Migration cancelled.")
        return False
    
    print("\n🚀 Running migration...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        
        # Execute migration
        cursor.execute(migration_sql)
        conn.commit()
        
        print("\n✅ Migration completed successfully!")
        print("\nNew structure:")
        print("  - mediator_sessions: stores session metadata")
        print("  - mediator_messages: stores entire conversation as JSON array")
        print("  - Format: [{\"role\": \"user\", \"content\": \"...\", \"timestamp\": \"...\"}, ...]")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
