import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from app.config import settings
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.services.s3_service import s3_service
from app.models.schemas import ConflictTranscript, SpeakerSegment

class ConflictManager:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.current_conflict_id = None
        self.relationship_id = None # In a real app, this would come from the token/context
        self.transcripts: List[Dict[str, Any]] = []
        self.is_recording = False

    async def start_conflict(self, relationship_id: str = None):
        """Starts a new conflict recording session."""
        self.current_conflict_id = str(uuid.uuid4())
        # For MVP, if no relationship_id is provided, we'll create a dummy one or use a fixed one
        # In production, this would be strictly enforced
        if not relationship_id:
            # Check if we have a default relationship, if not create one
            # For now, let's just use a hardcoded UUID for the "Demo Couple"
            self.relationship_id = "00000000-0000-0000-0000-000000000000" 
        else:
            self.relationship_id = relationship_id
            
        self.transcripts = []
        self.is_recording = True
        
        # Create initial record in DB using db_service (bypasses RLS)
        try:
            from app.services.db_service import db_service
            db_service.create_conflict(
                conflict_id=self.current_conflict_id,
                relationship_id=self.relationship_id,
                status="active"
            )
            print(f"✅ Started conflict {self.current_conflict_id} (stored in DB)")
        except ImportError:
            # Fallback to Supabase if db_service not available
            try:
                data = {
                    "id": self.current_conflict_id,
                    "relationship_id": self.relationship_id,
                    "started_at": datetime.now().isoformat(),
                    "status": "active"
                }
                self.supabase.table("conflicts").insert(data).execute()
                print(f"✅ Started conflict {self.current_conflict_id} (stored via Supabase)")
            except Exception as e:
                print(f"❌ Error starting conflict: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"❌ Error starting conflict: {e}")
            import traceback
            traceback.print_exc()

    def add_transcript(self, participant_identity: str, text: str, timestamp: float):
        """Adds a transcript segment to the buffer."""
        if not self.is_recording:
            return
            
        segment = {
            "speaker": participant_identity,
            "text": text,
            "timestamp": timestamp,
            "iso_time": datetime.now().isoformat()
        }
        self.transcripts.append(segment)
        # print(f"Recorded: {participant_identity}: {text}")

    async def end_conflict(self, partner_a_id: str = "partner_a", partner_b_id: str = "partner_b", speaker_labels: Optional[dict] = None):
        """Ends the conflict, uploads transcript to Storage, updates DB, and stores in Pinecone."""
        if not self.is_recording or not self.current_conflict_id:
            return

        self.is_recording = False
        start_time = datetime.now()  # Would be better to track actual start time
        ended_at = datetime.now()
        duration = (ended_at - start_time).total_seconds()
        
        # Build transcript text and speaker segments
        transcript_text = " ".join([seg["text"] for seg in self.transcripts])
        speaker_segments = [
            SpeakerSegment(
                speaker=seg["speaker"],
                text=seg["text"],
                start_time=seg.get("timestamp"),
                end_time=None  # Could calculate if we track end times
            )
            for seg in self.transcripts
        ]
        
        # Create ConflictTranscript model
        conflict_transcript = ConflictTranscript(
            conflict_id=self.current_conflict_id,
            relationship_id=self.relationship_id,
            transcript_text=transcript_text,
            speaker_segments=speaker_segments,
            timestamp=start_time,
            start_time=start_time,
            end_time=ended_at,
            duration=duration,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels or {}
        )
        
        file_path = f"transcripts/{self.relationship_id}/{self.current_conflict_id}.json"
        
        # 1. Store transcript in Pinecone (vector embeddings for semantic search)
        try:
            embedding = embeddings_service.embed_text(transcript_text)
            pinecone_service.upsert_transcript(
                conflict_id=self.current_conflict_id,
                embedding=embedding,
                transcript_data=conflict_transcript.model_dump(),
                namespace="transcripts"
            )
            print(f"✅ Stored transcript in Pinecone (vector embeddings) for conflict {self.current_conflict_id}")
        except Exception as e:
            print(f"❌ Error storing transcript in Pinecone: {e}")
            import traceback
            traceback.print_exc()
            # Continue - try Supabase storage even if Pinecone fails
        
        # 2. Upload raw transcript to AWS S3
        s3_url = None
        try:
            json_data = json.dumps(self.transcripts, indent=2)
            s3_url = s3_service.upload_file(
                file_path=file_path,
                file_content=json_data.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url:
                print(f"✅ Stored transcript in S3: {file_path} (URL: {s3_url})")
            else:
                print(f"❌ Failed to upload transcript to S3: {file_path}")
        except Exception as e:
            print(f"❌ Error uploading transcript to S3: {e}")
            import traceback
            traceback.print_exc()
            # Continue - update DB record even if storage fails

        # 3. Update Conflict Record in DB (always update, even if storage failed)
        try:
            update_data = {
                "ended_at": ended_at.isoformat(),
                "status": "completed",
                "metadata": {"utterance_count": len(self.transcripts)}
            }
            # Store S3 URL or path in database
            update_data["transcript_path"] = s3_url or file_path
            
            self.supabase.table("conflicts").update(update_data).eq("id", self.current_conflict_id).execute()
            print(f"✅ Updated conflict record for {self.current_conflict_id}")
        except Exception as e:
            print(f"❌ Error updating conflict record: {e}")
            import traceback
            traceback.print_exc()
            
        return self.current_conflict_id, conflict_transcript
