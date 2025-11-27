
import sys
import os
import json
from datetime import date

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.calendar_service import calendar_service

print("Fetching calendar events for Nov 2025...")
try:
    events = calendar_service.get_calendar_events(2025, 11)
    print(f"Total events: {len(events['events'])}")
    print(f"Stats: {json.dumps(events['stats'], indent=2)}")
    
    if len(events['events']) > 0:
        print("First 3 events:")
        for e in events['events'][:3]:
            print(f" - {e['event_date']} ({e['type']}): {e['title']}")
    else:
        print("❌ No events found!")

except Exception as e:
    print(f"❌ Error: {e}")
