import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from app.config import settings
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
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
        
        # Create initial record in DB
        data = {
            "id": self.current_conflict_id,
            "relationship_id": self.relationship_id,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # We might need to ensure the relationship exists first
        # For MVP, we'll skip that check and assume the migration created a default or we handle errors
        try:
            self.supabase.table("conflicts").insert(data).execute()
            print(f"Started conflict {self.current_conflict_id}")
        except Exception as e:
            print(f"Error starting conflict: {e}")

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
        
        # 1. Store transcript in Pinecone
        try:
            embedding = embeddings_service.embed_text(transcript_text)
            pinecone_service.upsert_transcript(
                conflict_id=self.current_conflict_id,
                embedding=embedding,
                transcript_data=conflict_transcript.model_dump(),
                namespace="transcripts"
            )
            print(f"✅ Stored transcript in Pinecone for conflict {self.current_conflict_id}")
        except Exception as e:
            print(f"❌ Error storing transcript in Pinecone: {e}")
        
        # 2. Upload raw transcript to Supabase Storage
        file_path = f"{self.relationship_id}/{self.current_conflict_id}.json"
        json_data = json.dumps(self.transcripts, indent=2)
        
        try:
            self.supabase.storage.from_("transcripts").upload(
                file_path,
                json_data.encode('utf-8'),
                {"content-type": "application/json"}
            )
            print(f"Uploaded transcript to {file_path}")
        except Exception as e:
            print(f"Error uploading transcript: {e}")

        # 3. Update Conflict Record in DB
        try:
            self.supabase.table("conflicts").update({
                "ended_at": ended_at.isoformat(),
                "status": "completed",
                "transcript_path": file_path,
                "metadata": {"utterance_count": len(self.transcripts)}
            }).eq("id", self.current_conflict_id).execute()
            print(f"Ended conflict {self.current_conflict_id}")
        except Exception as e:
            print(f"Error updating conflict record: {e}")
            
        return self.current_conflict_id, conflict_transcript
