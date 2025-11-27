"""
Database service for direct PostgreSQL access (bypasses Supabase RLS)
"""
import os
import json
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
    
    from contextlib import contextmanager

    @contextmanager
    def get_db_context(self):
        """Context manager for database connections that ensures closure"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                conn.close()

    def get_connection(self):
        """Get raw database connection (internal use)"""
        return psycopg2.connect(
            settings.DATABASE_URL,
            connect_timeout=5
        )
    
    def save_rant_message(self, conflict_id: str, partner_id: str, role: str, content: str) -> Optional[str]:
        """Save a rant message"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO rant_messages (conflict_id, partner_id, role, content, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (conflict_id, partner_id, role, content, datetime.now()))
                    
                    message_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(message_id)
        except Exception as e:
            # Connection is already closed by context manager, just raise
            raise e
    
    def get_rant_messages(self, conflict_id: str, partner_id: str) -> List[Dict[str, Any]]:
        """Get rant messages for a conflict and partner"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
                    return messages
        except Exception as e:
            raise e
    
    def list_conversations(self, conflict_id: str) -> List[Dict[str, Any]]:
        """List conversation sessions for a conflict"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO mediator_sessions (conflict_id, partner_id, session_started_at)
                        VALUES (%s, %s, %s)
                        RETURNING id;
                    """, (conflict_id, partner_id, datetime.now()))
                    
                    session_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(session_id)
        except Exception as e:
            raise e
    
    def end_mediator_session(self, session_id: str):
        """End a mediator session by setting session_ended_at"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE mediator_sessions
                        SET session_ended_at = %s
                        WHERE id = %s;
                    """, (datetime.now(), session_id))
                    
                    conn.commit()
        except Exception as e:
            raise e
    
    def save_mediator_message(self, session_id: str, role: str, content: str) -> Optional[str]:
        """
        Save a mediator message by appending to the conversation JSON array.
        Creates a new row if this is the first message, otherwise updates existing row.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Create message object
                    message_obj = {
                        "role": role,
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Try to insert a new row, or update if row already exists (using ON CONFLICT)
                    cursor.execute("""
                        INSERT INTO mediator_messages (session_id, content, created_at, updated_at)
                        VALUES (%s, %s::jsonb, %s, %s)
                        ON CONFLICT (session_id) DO UPDATE
                        SET 
                            content = mediator_messages.content || %s::jsonb,
                            updated_at = %s
                        RETURNING id;
                    """, (
                        session_id, 
                        json.dumps([message_obj]),  # For INSERT: array with one message
                        datetime.now(), 
                        datetime.now(),
                        json.dumps([message_obj]),  # For UPDATE: append to existing array
                        datetime.now()
                    ))
                    
                    message_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(message_id)
        except Exception as e:
            raise e
    
    def get_mediator_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a mediator session from the JSON content column.
        Returns messages in chronological order.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT content
                        FROM mediator_messages
                        WHERE session_id = %s;
                    """, (session_id,))
                    
                    row = cursor.fetchone()
                    
                    if row and row["content"]:
                        # Content is already a list of message objects
                        # PostgreSQL returns JSONB as Python dict/list automatically
                        messages = row["content"]
                        
                        # Ensure it's a list
                        if isinstance(messages, list):
                            return messages
                        else:
                            return []
                    
                    return []
        except Exception as e:
            raise e
    
    def get_mediator_sessions(self, conflict_id: str) -> List[Dict[str, Any]]:
        """Get all mediator sessions for a conflict"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO profiles (relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, datetime.now()))
                    
                    profile_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(profile_id)
        except Exception as e:
            raise e
    
    def get_profiles(self, relationship_id: str, pdf_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get profiles for a relationship, optionally filtered by pdf_type"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
                    return profiles
        except Exception as e:
            raise e
    
    def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a profile by ID"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, pdf_type, partner_id, filename, file_path, pdf_id, extracted_text_length, uploaded_at
                        FROM profiles
                        WHERE id = %s;
                    """, (profile_id,))
                    
                    row = cursor.fetchone()
                    
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
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO cycle_events (partner_id, event_type, timestamp, notes)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (partner_id, event_type, datetime.now(), notes))
                    
                    event_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(event_id)
        except Exception as e:
            raise e
    
    def create_intimacy_event(
        self,
        relationship_id: str,
        initiator_partner_id: Optional[str] = None
    ) -> str:
        """Create an intimacy event"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO intimacy_events (relationship_id, timestamp, initiator_partner_id)
                        VALUES (%s, %s, %s)
                        RETURNING id;
                    """, (relationship_id, datetime.now(), initiator_partner_id))
                    
                    event_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(event_id)
        except Exception as e:
            raise e
    
    def create_conflict_analysis(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis_path: str
    ) -> str:
        """Create or update a conflict analysis record (upsert)"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
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
                    return str(analysis_id)
        except Exception as e:
            # If ON CONFLICT not supported, try regular insert
            if "ON CONFLICT" in str(e) or "syntax error" in str(e).lower():
                try:
                    with self.get_db_context() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO conflict_analysis (conflict_id, relationship_id, analysis_path, analyzed_at)
                                VALUES (%s, %s, %s, %s)
                                RETURNING id;
                            """, (conflict_id, relationship_id, analysis_path, datetime.now()))
                            analysis_id = cursor.fetchone()[0]
                            conn.commit()
                            return str(analysis_id)
                except Exception:
                    # If insert fails (duplicate), that's okay - analysis already exists
                    return None
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
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
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
                    return str(plan_id)
        except Exception as e:
            # If ON CONFLICT not supported, try regular insert
            if "ON CONFLICT" in str(e) or "syntax error" in str(e).lower():
                try:
                    with self.get_db_context() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO repair_plans (conflict_id, relationship_id, partner_requesting, plan_path, generated_at)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id;
                            """, (conflict_id, relationship_id, partner_requesting, plan_path, datetime.now()))
                            plan_id = cursor.fetchone()[0]
                            conn.commit()
                            return str(plan_id)
                except Exception:
                    # If insert fails (duplicate), that's okay - plan already exists
                    return None
            raise e
    
    def get_conflict_analysis(
        self,
        conflict_id: str,
        relationship_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get existing conflict analysis by conflict_id"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
                    return plans
        except Exception as e:
            raise e
    
    def ensure_default_relationship(self) -> str:
        """Ensure the default relationship exists (creates if missing)"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Check if relationship exists
                    cursor.execute("""
                        SELECT id FROM relationships WHERE id = %s;
                    """, (DEFAULT_RELATIONSHIP_ID,))
                    
                    result = cursor.fetchone()
                    if result:
                        return DEFAULT_RELATIONSHIP_ID
                    
                    # Create relationship if it doesn't exist
                    cursor.execute("""
                        INSERT INTO relationships (id, partner_a_name, partner_b_name, created_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id;
                    """, (DEFAULT_RELATIONSHIP_ID, "Boyfriend", "Girlfriend", datetime.now()))
                    
                    conn.commit()
                    return DEFAULT_RELATIONSHIP_ID
        except Exception as e:
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
    ):
        """
        Create a conflict record (bypasses RLS) - uses default relationship ID
        """
        try:
            # Use default relationship ID if not provided
            if not relationship_id:
                relationship_id = DEFAULT_RELATIONSHIP_ID
                
            # Ensure relationship exists first
            self.get_or_create_relationship(relationship_id)
            
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO conflicts (id, relationship_id, status, started_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                    """, (conflict_id, relationship_id, status))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    if result:
                        return result[0]
                    return conflict_id
        except Exception as e:
            print(f"Error creating conflict: {e}")
            # Don't raise, just return None or log
            return None

    def get_conflict(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conflict details by ID (bypasses RLS).
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT *
                        FROM conflicts
                        WHERE id = %s
                    """, (conflict_id,))
                    
                    return cursor.fetchone()
        except Exception as e:
            print(f"Error getting conflict: {e}")
            return None

    def update_conflict_title(self, conflict_id: str, title: str) -> bool:
        """Update the title of a conflict"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE conflicts
                        SET title = %s
                        WHERE id = %s
                    """, (title, conflict_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating conflict title: {e}")
            return False
    
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
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
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
                    
                    return True
        except Exception as e:
            raise e
    
    def get_conflict_by_id(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Get a single conflict by ID (bypasses RLS)"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata, title
                        FROM conflicts
                        WHERE id = %s;
                    """, (conflict_id,))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        return {
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]) if row["relationship_id"] else None,
                            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                            "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                            "status": row["status"],
                            "transcript_path": row["transcript_path"],
                            "metadata": row["metadata"] if row["metadata"] else {},
                            "title": row["title"]
                        }
                    return None
        except Exception as e:
            raise e
    
    def get_all_conflicts(self, relationship_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conflicts, optionally filtered by relationship_id (bypasses RLS)"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if relationship_id:
                        cursor.execute("""
                            SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata, title
                            FROM conflicts
                            WHERE relationship_id = %s
                            ORDER BY started_at DESC;
                        """, (relationship_id,))
                    else:
                        cursor.execute("""
                            SELECT id, relationship_id, started_at, ended_at, status, transcript_path, metadata, title
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
                            "metadata": row["metadata"] if row["metadata"] else {},
                            "title": row["title"]
                        })
                    return conflicts
        except Exception as e:
            raise e
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None

    
    def get_conflict_transcript(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full transcript from rant_messages for a conflict.
        Returns transcript text and structured messages.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT partner_id, content, role, created_at
                        FROM rant_messages
                        WHERE conflict_id = %s
                        ORDER BY created_at
                    """, (conflict_id,))
                    
                    messages = cursor.fetchall()
                    if not messages:
                        return None
                    
                    transcript_lines = []
                    formatted_messages = []
                    
                    for msg in messages:
                        speaker = "Adrian Malhotra" if msg["partner_id"] == "partner_a" else "Elara Voss"
                        transcript_lines.append(f"{speaker}: {msg['content']}")
                        formatted_messages.append({
                            "partner_id": msg["partner_id"],
                            "speaker": speaker,
                            "content": msg["content"],
                            "role": msg["role"],
                            "created_at": msg["created_at"].isoformat() if msg["created_at"] else None
                        })
                    
                    return {
                        "conflict_id": conflict_id,
                        "transcript_text": "\n\n".join(transcript_lines),
                        "messages": formatted_messages,
                        "message_count": len(messages)
                    }
        except Exception as e:
            raise e
    
    def get_conflict_with_transcript(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conflict metadata along with full transcript.
        Combines data from conflicts and rant_messages tables.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get conflict metadata
                    cursor.execute("""
                        SELECT id, relationship_id, started_at, ended_at, 
                               status, duration_seconds, metadata
                        FROM conflicts
                        WHERE id = %s
                    """, (conflict_id,))
                    
                    conflict = cursor.fetchone()
                    if not conflict:
                        return None
                    
                    # Get transcript
                    transcript = self.get_conflict_transcript(conflict_id)
                    
                    return {
                        "id": str(conflict["id"]),
                        "relationship_id": str(conflict["relationship_id"]),
                        "started_at": conflict["started_at"].isoformat() if conflict["started_at"] else None,
                        "ended_at": conflict["ended_at"].isoformat() if conflict["ended_at"] else None,
                        "status": conflict["status"],
                        "duration_seconds": conflict["duration_seconds"],
                        "metadata": conflict["metadata"],
                        "transcript_text": transcript["transcript_text"] if transcript else "",
                        "messages": transcript["messages"] if transcript else [],
                        "message_count": transcript["message_count"] if transcript else 0
                    }
        except Exception as e:
            raise e

    def upsert_user(self, auth0_id: str, email: str, name: str, picture: str) -> str:
        """Upsert user and return user ID"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (auth0_id, email, name, picture, last_login)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (auth0_id) DO UPDATE SET
                            email = EXCLUDED.email,
                            name = EXCLUDED.name,
                            picture = EXCLUDED.picture,
                            last_login = EXCLUDED.last_login
                        RETURNING id;
                    """, (auth0_id, email, name, picture, datetime.now()))
                    
                    user_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(user_id)
        except Exception as e:
            raise e

# Global singleton instance
try:
    db_service = DatabaseService()
except Exception as e:
    print(f"❌ Failed to initialize DatabaseService: {e}")
    db_service = None
