import asyncio
import os
import sys
from datetime import date, timedelta

# Add backend directory to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.calendar_service import calendar_service
from app.services.db_service import DEFAULT_RELATIONSHIP_ID

async def seed_data():
    print("🌱 Seeding sample cycle data...")
    
    # Insert a period start date 2 weeks ago
    # This will give us a reference point for the heatmap
    # Nov 1, 2025 seems like a good start date based on the user's conflict history
    sample_date = date(2025, 11, 1)
    
    try:
        # We can use the synchronous method directly since we are in a script
        # But calendar_service methods are synchronous (they use db context managers)
        
        # Check if data already exists to avoid duplicates
        events = calendar_service.get_cycle_events(
            partner_id="partner_b",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 1)
        )
        
        if events:
            print(f"⚠️ Found {len(events)} existing cycle events. Skipping seed.")
            for e in events:
                print(f"   - {e['event_date']}: {e['event_type']}")
            return

        print(f"INSERTING period_start on {sample_date}...")
        event_id = calendar_service.create_cycle_event(
            partner_id="partner_b",
            event_type="period_start",
            event_date=sample_date,
            notes="Sample data for analytics",
            relationship_id=DEFAULT_RELATIONSHIP_ID
        )
        
        if event_id:
            print(f"✅ Successfully created sample period event (ID: {event_id})")
        else:
            print("❌ Failed to create event")

    except Exception as e:
        print(f"❌ Error seeding data: {e}")

if __name__ == "__main__":
    asyncio.run(seed_data())
