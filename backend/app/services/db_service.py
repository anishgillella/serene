"""
Database service for direct PostgreSQL access (bypasses Supabase RLS)
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

# Hardcoded single relationship ID for MVP
DEFAULT_RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"

class DatabaseService:
    """Service for direct database access"""
    
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        """Get database connection with timeout"""
        # Always create a fresh connection to avoid stale connection issues
        # Connection pooling can be added later if needed
        if self.conn:
            try:
                if not self.conn.closed:
                    self.conn.close()
            except:
                pass
            self.conn = None
        
        # Add connection timeout (5 seconds) to prevent hanging
        self.conn = psycopg2.connect(
            settings.DATABASE_URL,
            connect_timeout=5
        )
        return self.conn
    
    def save_rant_message(self, conflict_id: str, partner_id: str, role: str, content: str) -> Optional[str]:
        """Save a rant message"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO rant_messages (conflict_id, partner_id, role, content, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (conflict_id, partner_id, role, content, datetime.now()))
            
            message_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(message_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_rant_messages(self, conflict_id: str, partner_id: str) -> List[Dict[str, Any]]:
        """Get rant messages for a conflict and partner"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT role, content, created_at
                FROM rant_messages
                WHERE conflict_id = %s AND partner_id = %s
                ORDER BY created_at ASC;
            """, (conflict_id, partner_id))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            
            cursor.close()
            return messages
        except Exception as e:
            raise e
    
    def list_conversations(self, conflict_id: str) -> List[Dict[str, Any]]:
        """List conversation sessions for a conflict"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT partner_id, role, content, created_at
                FROM rant_messages
                WHERE conflict_id = %s
                ORDER BY created_at DESC;
            """, (conflict_id,))
            
            conversations = {}
            for row in cursor.fetchall():
                partner_id = row["partner_id"]
                created_at = row["created_at"]
                session_date = created_at.date().isoformat() if created_at else "unknown"
                session_key = f"{partner_id}_{session_date}"
                
                if session_key not in conversations:
                    conversations[session_key] = {
                        "partner_id": partner_id,
                        "session_date": session_date,
                        "first_message_at": created_at.isoformat() if created_at else "",
                        "last_message_at": created_at.isoformat() if created_at else "",
                        "message_count": 0,
                        "preview": ""
                    }
                
                conv = conversations[session_key]
                conv["message_count"] += 1
                if created_at:
                    if created_at.isoformat() > conv["last_message_at"]:
                        conv["last_message_at"] = created_at.isoformat()
                    if created_at.isoformat() < conv["first_message_at"]:
                        conv["first_message_at"] = created_at.isoformat()
                
                if row["role"] == "user" and not conv["preview"]:
                    conv["preview"] = row["content"][:100]
            
            cursor.close()
            
            # Convert to list and sort
            conversation_list = list(conversations.values())
            conversation_list.sort(key=lambda x: x["last_message_at"], reverse=True)
            
            return conversation_list
        except Exception as e:
            raise e
    
    def create_mediator_session(self, conflict_id: str, partner_id: Optional[str] = None) -> str:
        """Create a new mediator session and return session_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO mediator_sessions (conflict_id, partner_id, session_started_at)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (conflict_id, partner_id, datetime.now()))
            
            session_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(session_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def end_mediator_session(self, session_id: str):
        """End a mediator session by setting session_ended_at"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE mediator_sessions
                SET session_ended_at = %s
                WHERE id = %s;
            """, (datetime.now(), session_id))
            
            conn.commit()
            cursor.close()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def save_mediator_message(self, session_id: str, role: str, content: str) -> Optional[str]:
        """Save a mediator message (user or assistant/Luna)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO mediator_messages (session_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (session_id, role, content, datetime.now()))
            
            message_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(message_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_mediator_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a mediator session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT role, content, created_at
                FROM mediator_messages
                WHERE session_id = %s
                ORDER BY created_at ASC;
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                })
            
            cursor.close()
            return messages
        except Exception as e:
            raise e
    
    def get_mediator_sessions(self, conflict_id: str) -> List[Dict[str, Any]]:
        """Get all mediator sessions for a conflict"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, session_started_at, session_ended_at, partner_id
                FROM mediator_sessions
                WHERE conflict_id = %s
                ORDER BY session_started_at DESC;
            """, (conflict_id,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "session_id": str(row["id"]),
                    "session_started_at": row["session_started_at"].isoformat() if row["session_started_at"] else None,
                    "session_ended_at": row["session_ended_at"].isoformat() if row["session_ended_at"] else None,
                    "partner_id": row["partner_id"]
                })
            
            cursor.close()
            return sessions
        except Exception as e:
            raise e
    
    def create_profile(
        self,
        relationship_id: str,
        pdf_type: str,
        filename: str,
        file_path: str,
        pdf_id: str,
        extracted_text_length: int,
        partner_id: Optional[str] = None
    ) -> str:
        """Create a new profile record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO profiles (relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, datetime.now()))
            
            profile_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(profile_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_profiles(self, relationship_id: str, pdf_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get profiles for a relationship, optionally filtered by pdf_type"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if pdf_type:
                cursor.execute("""
                    SELECT id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at
                    FROM profiles
                    WHERE relationship_id = %s AND pdf_type = %s
                    ORDER BY uploaded_at DESC;
                """, (relationship_id, pdf_type))
            else:
                cursor.execute("""
                    SELECT id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at
                    FROM profiles
                    WHERE relationship_id = %s
                    ORDER BY uploaded_at DESC;
                """, (relationship_id,))
            
            profiles = []
            for row in cursor.fetchall():
                profiles.append({
                    "id": str(row["id"]),
                    "pdf_type": row["pdf_type"],
                    "partner_id": row["partner_id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "pdf_id": row["pdf_id"],
                    "extracted_text_length": row["extracted_text_length"],
                    "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None
                })
            
            cursor.close()
            return profiles
        except Exception as e:
            raise e
    
    def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a profile by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at
                FROM profiles
                WHERE id = %s;
            """, (profile_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "id": str(row["id"]),
                    "relationship_id": str(row["relationship_id"]),
                    "pdf_type": row["pdf_type"],
                    "partner_id": row["partner_id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "pdf_id": row["pdf_id"],
                    "extracted_text_length": row["extracted_text_length"],
                    "uploaded_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None
                }
            return None
        except Exception as e:
            raise e
    
    def create_cycle_event(
        self,
        partner_id: str,
        event_type: str,
        notes: Optional[str] = None
    ) -> str:
        """Create a cycle event"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cycle_events (partner_id, event_type, timestamp, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (partner_id, event_type, datetime.now(), notes))
            
            event_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(event_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def create_intimacy_event(
        self,
        relationship_id: str,
        initiator_partner_id: Optional[str] = None
    ) -> str:
        """Create an intimacy event"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO intimacy_events (relationship_id, timestamp, initiator_partner_id)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (relationship_id, datetime.now(), initiator_partner_id))
            
            event_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(event_id)
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def create_conflict_analysis(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis_path: str
    ) -> str:
        """Create or update a conflict analysis record (upsert)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use ON CONFLICT to update if exists, insert if not
            cursor.execute("""
                INSERT INTO conflict_analysis (conflict_id, relationship_id, analysis_path, analyzed_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (conflict_id, relationship_id) 
                DO UPDATE SET 
                    analysis_path = EXCLUDED.analysis_path,
                    analyzed_at = EXCLUDED.analyzed_at
                RETURNING id;
            """, (conflict_id, relationship_id, analysis_path, datetime.now()))
            
            analysis_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(analysis_id)
        except Exception as e:
            # If ON CONFLICT not supported, try regular insert
            if "ON CONFLICT" in str(e) or "syntax error" in str(e).lower():
                try:
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO conflict_analysis (conflict_id, relationship_id, analysis_path, analyzed_at)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (conflict_id, relationship_id, analysis_path, datetime.now()))
                    analysis_id = cursor.fetchone()[0]
                    conn.commit()
                    cursor.close()
                    return str(analysis_id)
                except Exception:
                    # If insert fails (duplicate), that's okay - analysis already exists
                    if self.conn:
                        self.conn.rollback()
                    return None
            if self.conn:
                self.conn.rollback()
            raise e
    
    def create_repair_plan(
        self,
        conflict_id: str,
        relationship_id: str,
        partner_requesting: str,
        plan_path: str
    ) -> str:
        """Create or update a repair plan record (upsert)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use ON CONFLICT to update if exists, insert if not
            cursor.execute("""
                INSERT INTO repair_plans (conflict_id, relationship_id, partner_requesting, plan_path, generated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (conflict_id, relationship_id, partner_requesting) 
                DO UPDATE SET 
                    plan_path = EXCLUDED.plan_path,
                    generated_at = EXCLUDED.generated_at
                RETURNING id;
            """, (conflict_id, relationship_id, partner_requesting, plan_path, datetime.now()))
            
            plan_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return str(plan_id)
        except Exception as e:
            # If ON CONFLICT not supported, try regular insert
            if "ON CONFLICT" in str(e) or "syntax error" in str(e).lower():
                try:
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO repair_plans (conflict_id, relationship_id, partner_requesting, plan_path, generated_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (conflict_id, relationship_id, partner_requesting, plan_path, datetime.now()))
                    plan_id = cursor.fetchone()[0]
                    conn.commit()
                    cursor.close()
                    return str(plan_id)
                except Exception:
                    # If insert fails (duplicate), that's okay - plan already exists
                    if self.conn:
                        self.conn.rollback()
                    return None
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_conflict_analysis(
        self,
        conflict_id: str,
        relationship_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get existing conflict analysis by conflict_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if relationship_id:
                cursor.execute("""
                    SELECT conflict_id, relationship_id, analysis_path, analyzed_at
                    FROM conflict_analysis
                    WHERE conflict_id = %s AND relationship_id = %s
                    ORDER BY analyzed_at DESC
                    LIMIT 1;
                """, (conflict_id, relationship_id))
            else:
                cursor.execute("""
                    SELECT conflict_id, relationship_id, analysis_path, analyzed_at
                    FROM conflict_analysis
                    WHERE conflict_id = %s
                    ORDER BY analyzed_at DESC
                    LIMIT 1;
                """, (conflict_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "conflict_id": str(row["conflict_id"]),
                    "relationship_id": str(row["relationship_id"]) if row["relationship_id"] else None,
                    "analysis_path": row["analysis_path"],
                    "analyzed_at": row["analyzed_at"].isoformat() if row["analyzed_at"] else None
                }
            return None
        except Exception as e:
            raise e
    
    def get_repair_plans(
        self,
        conflict_id: str,
        relationship_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get existing repair plans by conflict_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if relationship_id:
                cursor.execute("""
                    SELECT conflict_id, relationship_id, partner_requesting, plan_path, generated_at
                    FROM repair_plans
                    WHERE conflict_id = %s AND relationship_id = %s
                    ORDER BY generated_at DESC;
                """, (conflict_id, relationship_id))
            else:
                cursor.execute("""
                    SELECT conflict_id, relationship_id, partner_requesting, plan_path, generated_at
                    FROM repair_plans
                    WHERE conflict_id = %s
                    ORDER BY generated_at DESC;
                """, (conflict_id,))
            
            plans = []
            for row in cursor.fetchall():
                plans.append({
                    "conflict_id": str(row["conflict_id"]),
                    "relationship_id": str(row["relationship_id"]) if row["relationship_id"] else None,
                    "partner_requesting": row["partner_requesting"],
                    "plan_path": row["plan_path"],
                    "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None
                })
            
            cursor.close()
            return plans
        except Exception as e:
            raise e
    
    def ensure_default_relationship(self) -> str:
        """Ensure the default relationship exists (creates if missing)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if relationship exists
            cursor.execute("""
                SELECT id FROM relationships WHERE id = %s;
            """, (DEFAULT_RELATIONSHIP_ID,))
            
            result = cursor.fetchone()
            if result:
                cursor.close()
                return DEFAULT_RELATIONSHIP_ID
            
            # Create relationship if it doesn't exist
            cursor.execute("""
                INSERT INTO relationships (id, partner_a_name, partner_b_name, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                RETURNING id;
            """, (DEFAULT_RELATIONSHIP_ID, "Boyfriend", "Girlfriend", datetime.now()))
            
            conn.commit()
            cursor.close()
            return DEFAULT_RELATIONSHIP_ID
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_or_create_relationship(self, relationship_id: str = None, partner_a_name: str = "Partner A", partner_b_name: str = "Partner B") -> str:
        """Get existing relationship or create it if it doesn't exist (uses default relationship ID)"""
        # Always use default relationship ID for MVP
        return self.ensure_default_relationship()
    
    def create_conflict(
        self,
        conflict_id: str,
        relationship_id: str = None,
        status: str = "active"
    ) -> bool:
        """Create a conflict record (bypasses RLS) - uses default relationship ID"""
        try:
            # Always use default relationship ID for MVP
            relationship_id = DEFAULT_RELATIONSHIP_ID
            
            # Ensure relationship exists first
            self.ensure_default_relationship()
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conflicts (id, relationship_id, started_at, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    relationship_id = EXCLUDED.relationship_id,
                    status = EXCLUDED.status;
            """, (conflict_id, relationship_id, datetime.now(), status))
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def update_conflict(
        self,
        conflict_id: str,
        ended_at: Optional[datetime] = None,
        status: Optional[str] = None,
        transcript_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a conflict record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if ended_at is not None:
                updates.append("ended_at = %s")
                params.append(ended_at)
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            
            if transcript_path is not None:
                updates.append("transcript_path = %s")
                params.append(transcript_path)
            
            if metadata is not None:
                import json
                updates.append("metadata = %s::jsonb")
                params.append(json.dumps(metadata))
            
            if updates:
                params.append(conflict_id)
                query = f"""
                    UPDATE conflicts
                    SET {', '.join(updates)}
                    WHERE id = %s;
                """
                cursor.execute(query, params)
                conn.commit()
            
            cursor.close()
            return True
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_conflict_by_id(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conflict by ID (bypasses RLS)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata
                FROM conflicts
                WHERE id = %s;
            """, (conflict_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "id": str(row["id"]),
                    "relationship_id": str(row["relationship_id"]) if row["relationship_id"] else None,
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                    "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                    "status": row["status"],
                    "transcript_path": row["transcript_path"],
                    "metadata": row["metadata"] if row["metadata"] else {}
                }
            return None
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def get_all_conflicts(self, relationship_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conflicts, optionally filtered by relationship_id (bypasses RLS)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if relationship_id:
                cursor.execute("""
                    SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata
                    FROM conflicts
                    WHERE relationship_id = %s
                    ORDER BY started_at DESC;
                """, (relationship_id,))
            else:
                cursor.execute("""
                    SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata
                    FROM conflicts
                    ORDER BY started_at DESC;
                """)
            
            conflicts = []
            for row in cursor.fetchall():
                conflicts.append({
                    "id": str(row["id"]),
                    "relationship_id": str(row["relationship_id"]) if row["relationship_id"] else None,
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                    "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                    "status": row["status"],
                    "transcript_path": row["transcript_path"],
                    "metadata": row["metadata"] if row["metadata"] else {}
                })
            
            cursor.close()
            return conflicts
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise e
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None

# Global instance
try:
    db_service = DatabaseService()
except Exception as e:
    print(f"❌ Failed to initialize DatabaseService: {e}")
    db_service = None



