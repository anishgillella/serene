import sys
import os
import asyncio

# Add backend directory to path
backend_path = '/Users/anishgillella/Desktop/Stuff/Projects/Convo Mediator/serene/backend'
sys.path.append(backend_path)

from app.services.db_service import db_service

async def clear_onboarding_data():
    """
    Clear all onboarding profile data from the database.
    This includes partner profiles and relationship profiles.
    """
    print("🗑️  Starting onboarding data cleanup...")
    
    try:
        with db_service.get_db_context() as conn:
            with conn.cursor() as cursor:
                # First, check what data exists
                cursor.execute("SELECT COUNT(*) FROM partner_profiles;")
                partner_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM relationship_profiles;")
                relationship_count = cursor.fetchone()[0]
                
                print(f"📊 Found:")
                print(f"   - {partner_count} partner profile(s)")
                print(f"   - {relationship_count} relationship profile(s)")
                
                if partner_count == 0 and relationship_count == 0:
                    print("✨ No onboarding data to clear!")
                    return
                
                # Clear the data
                print("\n🧹 Clearing data...")
                
                # Delete partner profiles
                cursor.execute("DELETE FROM partner_profiles;")
                print(f"   ✅ Cleared {partner_count} partner profile(s)")
                
                # Delete relationship profiles  
                cursor.execute("DELETE FROM relationship_profiles;")
                print(f"   ✅ Cleared {relationship_count} relationship profile(s)")
                
                conn.commit()
                
                # Verify deletion
                cursor.execute("SELECT COUNT(*) FROM partner_profiles;")
                partner_remaining = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM relationship_profiles;")
                relationship_remaining = cursor.fetchone()[0]
                
                if partner_remaining == 0 and relationship_remaining == 0:
                    print("\n✅ Successfully cleared all onboarding data!")
                    print("💡 You can now re-submit onboarding with fresh sample data.")
                else:
                    print(f"\n⚠️  Warning: Some data may remain:")
                    print(f"   - Partner profiles: {partner_remaining}")
                    print(f"   - Relationship profiles: {relationship_remaining}")
                
    except Exception as e:
        print(f"💥 Error clearing onboarding data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(clear_onboarding_data())
