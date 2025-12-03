import asyncio
import os
from livekit import api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def cleanup():
    # Initialize LiveKit API
    url = os.getenv("LIVEKIT_URL")
    key = os.getenv("LIVEKIT_API_KEY")
    secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([url, key, secret]):
        print("❌ Error: Missing LiveKit credentials in .env")
        return

    lkapi = api.LiveKitAPI(url, key, secret)

    try:
        print("🔍 Fetching active rooms...")
        # List all rooms
        response = await lkapi.room.list_rooms(api.ListRoomsRequest())
        rooms = response.rooms
        
        if not rooms:
            print("✨ No active rooms found. All clean!")
            return

        print(f"🧹 Found {len(rooms)} active rooms. Cleaning up...")
        
        for room in rooms:
            print(f"   Deleting room: {room.name} ({room.sid})...")
            try:
                await lkapi.room.delete_room(api.DeleteRoomRequest(room=room.name))
                print(f"   ✅ Deleted {room.name}")
            except Exception as e:
                print(f"   ❌ Failed to delete {room.name}: {e}")

        print("\n🎉 Cleanup complete!")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(cleanup())
