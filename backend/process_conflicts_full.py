import asyncio
import os
import sys
import json
from datetime import datetime

# Add backend directory to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID
from app.services.calendar_service import calendar_service
from app.services.llm_service import llm_service
from app.tools.conflict_analysis import analyze_conflict_transcript
from app.tools.repair_coaching import generate_repair_plan

# Try to import s3_service, but handle failure
try:
    from app.services.s3_service import s3_service
    S3_AVAILABLE = True
except ImportError:
    s3_service = None
    S3_AVAILABLE = False
    print("⚠️ S3 Service not available. Analysis/Plans will be saved with dummy paths.")

async def process_conflicts():
    print("🚀 Starting Full Conflict Processing...")
    
    # 1. Get all conflicts
    conflicts = db_service.get_all_conflicts(DEFAULT_RELATIONSHIP_ID)
    print(f"Found {len(conflicts)} total conflicts.")
    
    deleted_count = 0
    processed_count = 0
    
    for conflict in conflicts:
        conflict_id = conflict["id"]
        date_str = conflict.get("started_at", "Unknown Date")
        
        # 2. Get Transcript (from Mediator Sessions)
        transcript = ""
        with db_service.get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT mm.content
                    FROM mediator_sessions ms
                    JOIN mediator_messages mm ON ms.id = mm.session_id
                    WHERE ms.conflict_id = %s
                    ORDER BY ms.session_started_at DESC
                    LIMIT 1
                """, (conflict_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    messages = row[0]
                    lines = []
                    for msg in messages:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        lines.append(f"{role}: {content}")
                    transcript = "\n".join(lines)
        
        # 3. Delete if no transcript
        if not transcript:
            print(f"🗑️  Deleting empty conflict {conflict_id} ({date_str})...")
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM conflicts WHERE id = %s", (conflict_id,))
                    conn.commit()
            deleted_count += 1
            continue
            
        print(f"⚡ Processing {conflict_id} ({date_str})...")
        
        # 4. Generate Title & Topics
        # This updates the DB metadata directly
        topics = calendar_service.extract_and_store_conflict_topics(conflict_id)
        
        # Also ensure the title column is updated
        with db_service.get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT metadata FROM conflicts WHERE id = %s", (conflict_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    metadata = row[0]
                    title = metadata.get("title")
                    if title:
                        cursor.execute("UPDATE conflicts SET title = %s WHERE id = %s", (title, conflict_id))
                        conn.commit()
                        print(f"   ✅ Title column updated: '{title}'")
        
        print(f"   ✅ Topics/Title generated")
        
        # 5. Generate Analysis
        try:
            analysis = await analyze_conflict_transcript(
                conflict_id=conflict_id,
                transcript_text=transcript,
                relationship_id=DEFAULT_RELATIONSHIP_ID,
                partner_a_id="partner_a",
                partner_b_id="partner_b",
                speaker_labels={"partner_a": "Boyfriend", "partner_b": "Girlfriend"},
                duration=0,
                timestamp=datetime.now()
            )
            
            # Save Analysis
            analysis_json = json.dumps(analysis.model_dump(), default=str, indent=2)
            analysis_path = f"analysis/{DEFAULT_RELATIONSHIP_ID}/{conflict_id}_analysis.json"
            
            if S3_AVAILABLE:
                try:
                    s3_url = s3_service.upload_file(
                        file_path=analysis_path,
                        file_content=analysis_json.encode('utf-8'),
                        content_type="application/json"
                    )
                    if s3_url:
                        analysis_path = s3_url
                except Exception as e:
                    print(f"   ⚠️ S3 Upload failed: {e}")
            
            db_service.create_conflict_analysis(conflict_id, DEFAULT_RELATIONSHIP_ID, analysis_path)
            print(f"   ✅ Analysis generated & saved")
            
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")

        # 6. Generate Repair Plans
        try:
            # Boyfriend Plan
            plan_bf = await generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript,
                partner_requesting_id="partner_a",
                relationship_id=DEFAULT_RELATIONSHIP_ID,
                partner_a_id="partner_a",
                partner_b_id="partner_b",
                include_calendar=True
            )
            
            plan_bf_json = json.dumps(plan_bf.model_dump(), default=str, indent=2)
            plan_bf_path = f"repair_plans/{DEFAULT_RELATIONSHIP_ID}/{conflict_id}_repair_partner_a.json"
            
            if S3_AVAILABLE:
                try:
                    s3_url = s3_service.upload_file(plan_bf_path, plan_bf_json.encode('utf-8'), "application/json")
                    if s3_url: plan_bf_path = s3_url
                except: pass
                
            db_service.create_repair_plan(conflict_id, DEFAULT_RELATIONSHIP_ID, "partner_a", plan_bf_path)
            
            # Girlfriend Plan
            plan_gf = await generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript,
                partner_requesting_id="partner_b",
                relationship_id=DEFAULT_RELATIONSHIP_ID,
                partner_a_id="partner_a",
                partner_b_id="partner_b",
                include_calendar=True
            )
            
            plan_gf_json = json.dumps(plan_gf.model_dump(), default=str, indent=2)
            plan_gf_path = f"repair_plans/{DEFAULT_RELATIONSHIP_ID}/{conflict_id}_repair_partner_b.json"
            
            if S3_AVAILABLE:
                try:
                    s3_url = s3_service.upload_file(plan_gf_path, plan_gf_json.encode('utf-8'), "application/json")
                    if s3_url: plan_gf_path = s3_url
                except: pass
                
            db_service.create_repair_plan(conflict_id, DEFAULT_RELATIONSHIP_ID, "partner_b", plan_gf_path)
            
            print(f"   ✅ Repair plans generated & saved")
            
        except Exception as e:
            print(f"   ❌ Repair plans failed: {e}")
            
        processed_count += 1

    print(f"\n✨ Processing Complete!")
    print(f"Deleted (Empty): {deleted_count}")
    print(f"Processed (Enriched): {processed_count}")

if __name__ == "__main__":
    asyncio.run(process_conflicts())
