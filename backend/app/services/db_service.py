"""
Database service for direct PostgreSQL access (bypasses Supabase RLS)
"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings

# Default relationship ID for backward compatibility (Adrian & Elara test data)
# This is kept for MVP/testing purposes only
DEFAULT_RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"

# Multi-tenancy: relationship_id should now be passed dynamically via:
# - URL query parameter: ?relationship_id=xxx
# - Request header: X-Relationship-ID
# - localStorage on frontend (persisted per browser)

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
            
    def save_transcript_messages(self, conflict_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        Batch save transcript messages to rant_messages table.
        messages should be a list of dicts with: partner_id, role, content
        Uses sequence_number for explicit ordering to preserve conversation flow.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Prepare values for batch insert
                    values = []
                    now = datetime.now()
                    for i, msg in enumerate(messages):
                        values.append((
                            conflict_id,
                            msg["partner_id"],
                            msg["role"],
                            msg["content"],
                            now,
                            i  # sequence_number - explicit ordering
                        ))

                    # Execute batch insert with sequence_number
                    from psycopg2.extras import execute_values
                    execute_values(cursor, """
                        INSERT INTO rant_messages (conflict_id, partner_id, role, content, created_at, sequence_number)
                        VALUES %s
                    """, values)

                    conn.commit()
                    print(f"✅ Saved {len(messages)} transcript messages with sequence numbers")
                    return True
        except Exception as e:
            print(f"Error batch saving transcript messages: {e}")
            return False
    
    def get_rant_messages(self, conflict_id: str, partner_id: str) -> List[Dict[str, Any]]:
        """Get rant messages for a conflict and partner"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Check if sequence_number column exists
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'rant_messages' AND column_name = 'sequence_number'
                    """)
                    has_sequence_number = cursor.fetchone() is not None

                    if has_sequence_number:
                        cursor.execute("""
                            SELECT role, content, created_at, sequence_number
                            FROM rant_messages
                            WHERE conflict_id = %s AND partner_id = %s
                            ORDER BY sequence_number ASC, created_at ASC;
                        """, (conflict_id, partner_id))
                    else:
                        cursor.execute("""
                            SELECT role, content, created_at, 0 as sequence_number
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

    def update_profile(self, pdf_id: str, updates: Dict[str, Any]) -> bool:
        """Update profile fields"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    set_clauses = []
                    values = []
                    for key, value in updates.items():
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                    
                    if not set_clauses:
                        return False
                        
                    values.append(pdf_id)
                    query = f"""
                        UPDATE profiles 
                        SET {', '.join(set_clauses)}
                        WHERE pdf_id = %s
                    """
                    cursor.execute(query, values)
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False

    def delete_profile(self, pdf_id: str) -> bool:
        """Delete a profile/PDF record by ID"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM profiles WHERE pdf_id = %s", (pdf_id,))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
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

    def delete_conflict(self, conflict_id: str) -> bool:
        """Delete a conflict and all associated data (cascade should handle most, but explicit for safety)"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Delete related records first (if cascade not set up, though it should be)
                    # Deleting from conflicts table should cascade to analysis, repair_plans, etc.
                    # But let's be safe and explicit or rely on cascade.
                    # Assuming cascade is set up in migration.sql. If not, we need to delete children first.
                    # Let's assume cascade for now, but wrap in transaction.

                    # Cast to UUID explicitly to ensure proper type matching
                    cursor.execute("DELETE FROM conflicts WHERE id = %s::uuid", (conflict_id,))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"✅ Deleted conflict {conflict_id}, rows affected: {deleted_count}")
                    return deleted_count > 0
        except Exception as e:
            print(f"❌ Error deleting conflict {conflict_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_conflicts_by_title(self, title: str) -> int:
        """Delete all conflicts with a specific title (e.g. 'Conflict Session')"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM conflicts WHERE title = %s", (title,))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    return deleted_count
        except Exception as e:
            print(f"Error deleting conflicts by title: {e}")
            return 0

    def delete_conflicts_bulk(self, conflict_ids: List[str]) -> int:
        """Delete multiple conflicts by their IDs"""
        if not conflict_ids:
            return 0
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Use ANY with array for efficient bulk delete, cast to UUID array
                    cursor.execute(
                        "DELETE FROM conflicts WHERE id = ANY(%s::uuid[])",
                        (conflict_ids,)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"✅ Bulk deleted {deleted_count} conflicts out of {len(conflict_ids)} requested")
                    return deleted_count
        except Exception as e:
            print(f"❌ Error bulk deleting conflicts: {e}")
            import traceback
            traceback.print_exc()
            return 0

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
        Orders by sequence_number to preserve conversation flow.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Check if sequence_number column exists
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'rant_messages' AND column_name = 'sequence_number'
                    """)
                    has_sequence_number = cursor.fetchone() is not None

                    if has_sequence_number:
                        cursor.execute("""
                            SELECT partner_id, content, role, created_at, sequence_number
                            FROM rant_messages
                            WHERE conflict_id = %s
                            ORDER BY sequence_number ASC, created_at ASC
                        """, (conflict_id,))
                    else:
                        # Fallback if sequence_number column doesn't exist
                        cursor.execute("""
                            SELECT partner_id, content, role, created_at, 0 as sequence_number
                            FROM rant_messages
                            WHERE conflict_id = %s
                            ORDER BY created_at ASC
                        """, (conflict_id,))
                    
                    messages = cursor.fetchall()
                    if not messages:
                        return None
                    
                    transcript_lines = []
                    formatted_messages = []
                    
                    # Get dynamic speaker names based on relationship
                    # First try to get relationship_id from the conflict
                    speaker_labels = {"partner_a": "Partner A", "partner_b": "Partner B"}
                    if messages:
                        try:
                            cursor.execute("""
                                SELECT c.relationship_id, r.partner_a_name, r.partner_b_name
                                FROM conflicts c
                                LEFT JOIN relationships r ON c.relationship_id = r.id
                                WHERE c.id = %s;
                            """, (conflict_id,))
                            rel_row = cursor.fetchone()
                            if rel_row and rel_row.get("partner_a_name"):
                                speaker_labels["partner_a"] = rel_row["partner_a_name"]
                            if rel_row and rel_row.get("partner_b_name"):
                                speaker_labels["partner_b"] = rel_row["partner_b_name"]
                        except Exception:
                            pass

                    for msg in messages:
                        speaker = speaker_labels.get(msg["partner_id"], "Speaker")
                        transcript_lines.append(f"{speaker}: {msg['content']}")
                        formatted_messages.append({
                            "partner_id": msg["partner_id"],
                            "speaker": speaker,
                            "content": msg["content"],
                            "role": msg["role"],
                            "created_at": msg["created_at"].isoformat() if msg["created_at"] else None,
                            "sequence_number": msg.get("sequence_number", 0)
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
                               status, metadata
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

    def store_chat_message(self, conflict_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a chat message"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO chat_messages (conflict_id, role, content, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (conflict_id, role, content, json.dumps(metadata) if metadata else '{}', datetime.now()))
                    
                    message_id = cursor.fetchone()[0]
                    conn.commit()
                    return str(message_id)
        except Exception as e:
            raise e

    def get_chat_history(self, conflict_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a conflict"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, role, content, metadata, created_at
                        FROM chat_messages
                        WHERE conflict_id = %s
                        ORDER BY created_at ASC
                        LIMIT %s;
                    """, (conflict_id, limit))
                    
                    messages = []
                    for row in cursor.fetchall():
                        messages.append({
                            "id": str(row["id"]),
                            "role": row["role"],
                            "content": row["content"],
                            "metadata": row["metadata"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None
                        })
                    return messages
        except Exception as e:
            raise e

    # ============================================
    # User & Relationship Context Methods (Phase 1)
    # ============================================

    def get_user_by_auth0_id(self, auth0_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Auth0 ID (sub claim)."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, auth0_id, email, name, picture, created_at, last_login
                        FROM users
                        WHERE auth0_id = %s;
                    """, (auth0_id,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            print(f"Error getting user by auth0_id: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by internal user ID."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, auth0_id, email, name, picture, created_at, last_login
                        FROM users
                        WHERE id = %s;
                    """, (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None

    def get_user_relationship_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's relationship context including partner info.

        Returns:
            {
                "relationship_id": str,
                "display_name": str,
                "partner_display_name": str,
                "role": str
            }
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT
                            rm.relationship_id,
                            rm.display_name,
                            rm.role,
                            partner.display_name as partner_display_name,
                            partner.user_id as partner_user_id
                        FROM relationship_members rm
                        LEFT JOIN relationship_members partner
                            ON partner.relationship_id = rm.relationship_id
                            AND partner.user_id != rm.user_id
                            AND partner.invitation_status = 'accepted'
                        WHERE rm.user_id = %s
                            AND rm.invitation_status = 'accepted'
                        LIMIT 1;
                    """, (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            "relationship_id": str(row["relationship_id"]),
                            "display_name": row["display_name"],
                            "partner_display_name": row["partner_display_name"],
                            "role": row["role"],
                            "partner_user_id": str(row["partner_user_id"]) if row["partner_user_id"] else None
                        }
                    return None
        except Exception as e:
            print(f"Error getting user relationship context: {e}")
            return None

    def get_speaker_labels(self, relationship_id: str) -> Dict[str, str]:
        """
        Get speaker labels for a relationship (for transcript display).

        Returns:
            {
                "partner_a": "Adrian",
                "partner_b": "Elara"
            }
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT
                            display_name,
                            joined_at
                        FROM relationship_members
                        WHERE relationship_id = %s
                            AND invitation_status = 'accepted'
                        ORDER BY joined_at ASC;
                    """, (relationship_id,))
                    rows = cursor.fetchall()

                    labels = {"partner_a": "Partner A", "partner_b": "Partner B"}
                    for i, row in enumerate(rows):
                        if i == 0:
                            labels["partner_a"] = row["display_name"] or "Partner A"
                        elif i == 1:
                            labels["partner_b"] = row["display_name"] or "Partner B"

                    return labels
        except Exception as e:
            print(f"Error getting speaker labels: {e}")
            return {"partner_a": "Partner A", "partner_b": "Partner B"}

    def create_user_with_relationship(
        self,
        auth0_id: str,
        email: str,
        name: Optional[str],
        display_name: str
    ) -> tuple:
        """
        Create a new user and their relationship.

        Returns:
            (user_id, relationship_id)
        """
        import uuid
        user_id = str(uuid.uuid4())
        relationship_id = str(uuid.uuid4())

        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Create or update user
                    cursor.execute("""
                        INSERT INTO users (id, auth0_id, email, name, created_at, last_login)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (auth0_id) DO UPDATE SET
                            email = EXCLUDED.email,
                            name = EXCLUDED.name,
                            last_login = NOW()
                        RETURNING id;
                    """, (user_id, auth0_id, email, name))
                    user_id = str(cursor.fetchone()[0])

                    # Create relationship
                    cursor.execute("""
                        INSERT INTO relationships (id, created_at, partner_a_name)
                        VALUES (%s, NOW(), %s);
                    """, (relationship_id, display_name))

                    # Link user to relationship
                    cursor.execute("""
                        INSERT INTO relationship_members
                            (user_id, relationship_id, role, display_name, invitation_status, joined_at)
                        VALUES (%s, %s, 'partner', %s, 'accepted', NOW());
                    """, (user_id, relationship_id, display_name))

                    conn.commit()
                    return (user_id, relationship_id)
        except Exception as e:
            print(f"Error creating user with relationship: {e}")
            raise e

    def resolve_relationship_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve full relationship context for a user.

        Returns:
            {
                "relationship_id": str,
                "user_role": str,  # "partner_a" or "partner_b"
                "display_name": str,
                "partner_display_name": str,
                "partner_user_id": str | None
            }
        """
        context = self.get_user_relationship_context(user_id)
        if not context:
            return None

        # Determine user role based on join order
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT user_id
                        FROM relationship_members
                        WHERE relationship_id = %s
                            AND invitation_status = 'accepted'
                        ORDER BY joined_at ASC
                        LIMIT 1;
                    """, (context["relationship_id"],))
                    first_member = cursor.fetchone()

                    if first_member and str(first_member["user_id"]) == user_id:
                        context["user_role"] = "partner_a"
                    else:
                        context["user_role"] = "partner_b"

                    return context
        except Exception as e:
            print(f"Error resolving relationship context: {e}")
            context["user_role"] = "partner_a"  # Default
            return context

    # ============================================
    # Multi-Tenancy Methods (Phase 2)
    # ============================================

    def create_relationship(self, partner_a_name: str, partner_b_name: str) -> str:
        """
        Create a new relationship with partner names.
        Returns the new relationship_id.
        """
        import uuid
        relationship_id = str(uuid.uuid4())

        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Create relationship
                    cursor.execute("""
                        INSERT INTO relationships (id, partner_a_name, partner_b_name, created_at)
                        VALUES (%s, %s, %s, NOW())
                        RETURNING id;
                    """, (relationship_id, partner_a_name, partner_b_name))

                    relationship_id = str(cursor.fetchone()[0])

                    # Create couple_profile for easy access
                    cursor.execute("""
                        INSERT INTO couple_profiles (relationship_id, partner_a_name, partner_b_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (relationship_id) DO NOTHING;
                    """, (relationship_id, partner_a_name, partner_b_name))

                    conn.commit()
                    return relationship_id
        except Exception as e:
            print(f"Error creating relationship: {e}")
            raise e

    def get_relationship(self, relationship_id: str) -> Optional[Dict[str, Any]]:
        """Get relationship details by ID."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT r.id, r.partner_a_name, r.partner_b_name, r.created_at,
                               r.partner_a_id, r.partner_b_id
                        FROM relationships r
                        WHERE r.id = %s;
                    """, (relationship_id,))

                    row = cursor.fetchone()
                    if row:
                        return {
                            "id": str(row["id"]),
                            "partner_a_name": row["partner_a_name"] or "Partner A",
                            "partner_b_name": row["partner_b_name"] or "Partner B",
                            "partner_a_id": str(row["partner_a_id"]) if row["partner_a_id"] else None,
                            "partner_b_id": str(row["partner_b_id"]) if row["partner_b_id"] else None,
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None
                        }
                    return None
        except Exception as e:
            print(f"Error getting relationship: {e}")
            return None

    def update_relationship_names(self, relationship_id: str, partner_a_name: str = None, partner_b_name: str = None) -> bool:
        """Update partner names for a relationship."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    updates = []
                    params = []

                    if partner_a_name:
                        updates.append("partner_a_name = %s")
                        params.append(partner_a_name)

                    if partner_b_name:
                        updates.append("partner_b_name = %s")
                        params.append(partner_b_name)

                    if not updates:
                        return True

                    params.append(relationship_id)

                    # Update relationships table
                    cursor.execute(f"""
                        UPDATE relationships
                        SET {', '.join(updates)}
                        WHERE id = %s;
                    """, params)

                    # Also update couple_profiles table
                    cursor.execute("""
                        UPDATE couple_profiles
                        SET partner_a_name = COALESCE(%s, partner_a_name),
                            partner_b_name = COALESCE(%s, partner_b_name),
                            updated_at = NOW()
                        WHERE relationship_id = %s;
                    """, (partner_a_name, partner_b_name, relationship_id))

                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating relationship names: {e}")
            return False

    def get_couple_profile(self, relationship_id: str) -> Optional[Dict[str, Any]]:
        """Get couple profile by relationship_id."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, partner_a_name, partner_b_name,
                               created_at, updated_at, metadata
                        FROM couple_profiles
                        WHERE relationship_id = %s;
                    """, (relationship_id,))

                    row = cursor.fetchone()
                    if row:
                        return {
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]),
                            "partner_a_name": row["partner_a_name"],
                            "partner_b_name": row["partner_b_name"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                            "metadata": row["metadata"] or {}
                        }
                    return None
        except Exception as e:
            print(f"Error getting couple profile: {e}")
            return None

    def get_partner_names(self, relationship_id: str) -> Dict[str, str]:
        """
        Get partner names for a relationship.
        Returns dict with partner_a and partner_b names.
        Falls back to defaults if not found.
        """
        try:
            relationship = self.get_relationship(relationship_id)
            if relationship:
                return {
                    "partner_a": relationship.get("partner_a_name") or "Partner A",
                    "partner_b": relationship.get("partner_b_name") or "Partner B"
                }
            return {"partner_a": "Partner A", "partner_b": "Partner B"}
        except Exception as e:
            print(f"Error getting partner names: {e}")
            return {"partner_a": "Partner A", "partner_b": "Partner B"}

    def get_dynamic_speaker_labels(self, relationship_id: str) -> Dict[str, str]:
        """
        Get speaker labels for transcripts based on relationship.
        Maps partner_a/partner_b to actual names.
        """
        names = self.get_partner_names(relationship_id)
        return {
            "partner_a": names["partner_a"],
            "partner_b": names["partner_b"]
        }

    def validate_relationship_exists(self, relationship_id: str) -> bool:
        """Check if a relationship exists."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 1 FROM relationships WHERE id = %s;
                    """, (relationship_id,))
                    return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error validating relationship: {e}")
            return False

    # ============================================
    # Security & Audit Methods (Phase 5)
    # ============================================

    def create_audit_log(self, log_entry: Dict[str, Any]) -> bool:
        """Create an audit log entry."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO audit_logs (
                            action, table_name, record_id, relationship_id,
                            ip_address, user_agent, request_path, request_method,
                            status_code, error_message, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        log_entry.get("action"),
                        log_entry.get("table_name"),
                        log_entry.get("record_id"),
                        log_entry.get("relationship_id"),
                        log_entry.get("ip_address"),
                        log_entry.get("user_agent"),
                        log_entry.get("request_path"),
                        log_entry.get("request_method"),
                        log_entry.get("status_code"),
                        log_entry.get("error_message"),
                        json.dumps(log_entry.get("metadata", {}))
                    ))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error creating audit log: {e}")
            return False

    def get_audit_logs(
        self,
        relationship_id: str = None,
        action: str = None,
        table_name: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit logs with optional filters."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = "SELECT * FROM audit_logs WHERE 1=1"
                    params = []

                    if relationship_id:
                        query += " AND relationship_id = %s"
                        params.append(relationship_id)
                    if action:
                        query += " AND action = %s"
                        params.append(action)
                    if table_name:
                        query += " AND table_name = %s"
                        params.append(table_name)

                    query += " ORDER BY timestamp DESC LIMIT %s"
                    params.append(limit)

                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting audit logs: {e}")
            return []

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int = 60,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check and update rate limit for an identifier.
        Returns (is_allowed, remaining_requests).
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    now = datetime.now()
                    window_start = now - timedelta(seconds=window_seconds)

                    # Get current count
                    cursor.execute("""
                        SELECT request_count, window_start
                        FROM rate_limits
                        WHERE identifier = %s AND endpoint = %s
                        AND window_start > %s;
                    """, (identifier, endpoint, window_start))

                    row = cursor.fetchone()

                    if row:
                        current_count = row["request_count"]
                        if current_count >= limit:
                            return False, 0

                        # Update count
                        cursor.execute("""
                            UPDATE rate_limits
                            SET request_count = request_count + 1, updated_at = NOW()
                            WHERE identifier = %s AND endpoint = %s;
                        """, (identifier, endpoint))
                        conn.commit()
                        return True, limit - current_count - 1
                    else:
                        # Create new entry
                        cursor.execute("""
                            INSERT INTO rate_limits (identifier, endpoint, request_count, window_start, window_end)
                            VALUES (%s, %s, 1, %s, %s)
                            ON CONFLICT (identifier, endpoint) DO UPDATE
                            SET request_count = 1, window_start = %s, window_end = %s, updated_at = NOW();
                        """, (
                            identifier, endpoint, now, now + timedelta(seconds=window_seconds),
                            now, now + timedelta(seconds=window_seconds)
                        ))
                        conn.commit()
                        return True, limit - 1

        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return True, limit  # Allow on error

    # ========================================================================
    # Phase 1: Conflict Enrichment Methods
    # ========================================================================

    def save_trigger_phrase(self, relationship_id: str, conflict_id: str, phrase_data: dict) -> bool:
        """Save a trigger phrase to the database"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO trigger_phrases (
                            relationship_id, conflict_id, phrase, phrase_category,
                            emotional_intensity, references_past_conflict, speaker,
                            is_pattern_trigger, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        relationship_id,
                        conflict_id,
                        phrase_data.get('phrase'),
                        phrase_data.get('phrase_category'),
                        phrase_data.get('emotional_intensity', 5),
                        phrase_data.get('references_past', False),
                        phrase_data.get('speaker'),
                        phrase_data.get('is_escalation_trigger', False),
                        datetime.now()
                    ))

                    phrase_id = cursor.fetchone()[0]
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error saving trigger phrase: {e}")
            return False

    def save_unmet_need(self, relationship_id: str, conflict_id: str, need_data: dict) -> bool:
        """Save an unmet need to the database"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO unmet_needs (
                            relationship_id, conflict_id, need, identified_by,
                            confidence, speaker, evidence, first_identified_at,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (
                        relationship_id,
                        conflict_id,
                        need_data.get('need'),
                        need_data.get('identified_by', 'gpt_analysis'),
                        need_data.get('confidence', 0.5),
                        need_data.get('speaker'),
                        need_data.get('evidence'),
                        datetime.now(),
                        datetime.now()
                    ))

                    need_id = cursor.fetchone()[0]
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error saving unmet need: {e}")
            return False

    def update_conflict(
        self,
        conflict_id: str,
        parent_conflict_id: Optional[str] = None,
        resentment_level: Optional[int] = None,
        has_past_references: Optional[bool] = None,
        is_continuation: Optional[bool] = None,
        unmet_needs: Optional[List[str]] = None
    ) -> bool:
        """Update conflict with enrichment data"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    updates = []
                    values = []

                    if parent_conflict_id is not None:
                        updates.append("parent_conflict_id = %s")
                        values.append(parent_conflict_id)

                    if resentment_level is not None:
                        updates.append("resentment_level = %s")
                        values.append(resentment_level)

                    if has_past_references is not None:
                        updates.append("has_past_references = %s")
                        values.append(has_past_references)

                    if is_continuation is not None:
                        updates.append("is_continuation = %s")
                        values.append(is_continuation)

                    if unmet_needs is not None:
                        updates.append("unmet_needs = %s")
                        values.append(unmet_needs)

                    if not updates:
                        return True

                    # Add conflict_id at the end for the WHERE clause
                    values.append(conflict_id)

                    update_clause = ", ".join(updates)
                    cursor.execute(f"""
                        UPDATE conflicts
                        SET {update_clause}
                        WHERE id = %s;
                    """, values)

                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error updating conflict enrichment: {e}")
            return False

    def get_previous_conflicts(
        self, relationship_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get previous conflicts for a relationship"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, started_at, metadata, resentment_level, unmet_needs,
                               is_resolved, resolved_at
                        FROM conflicts
                        WHERE relationship_id = %s
                        ORDER BY started_at DESC
                        LIMIT %s;
                    """, (relationship_id, limit))

                    return cursor.fetchall() if cursor.rowcount > 0 else []
        except Exception as e:
            print(f"Error getting previous conflicts: {e}")
            return []

    def get_trigger_phrases_for_relationship(
        self, relationship_id: str
    ) -> List[Dict[str, Any]]:
        """Get all trigger phrases for a relationship"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT phrase, phrase_category, speaker,
                               COUNT(*) as usage_count,
                               AVG(emotional_intensity) as avg_intensity,
                               COUNT(CASE WHEN is_pattern_trigger THEN 1 END)::FLOAT / COUNT(*) as escalation_rate
                        FROM trigger_phrases
                        WHERE relationship_id = %s
                        GROUP BY phrase, phrase_category, speaker
                        ORDER BY usage_count DESC;
                    """, (relationship_id,))

                    return cursor.fetchall() if cursor.rowcount > 0 else []
        except Exception as e:
            print(f"Error getting trigger phrases: {e}")
            return []

    def get_unmet_needs_for_relationship(
        self, relationship_id: str
    ) -> List[Dict[str, Any]]:
        """Get chronic unmet needs for a relationship"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT need,
                               COUNT(DISTINCT conflict_id) as conflict_count,
                               MIN(first_identified_at) as first_appeared,
                               COUNT(DISTINCT DATE(created_at)) as days_appeared_in,
                               CASE WHEN COUNT(DISTINCT conflict_id) >= 3 THEN TRUE ELSE FALSE END as is_chronic
                        FROM unmet_needs
                        WHERE relationship_id = %s
                        GROUP BY need
                        ORDER BY conflict_count DESC;
                    """, (relationship_id,))

                    return cursor.fetchall() if cursor.rowcount > 0 else []
        except Exception as e:
            print(f"Error getting unmet needs: {e}")
            return []

    def get_conflict(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conflict by ID"""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM conflicts WHERE id = %s;
                    """, (conflict_id,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"Error getting conflict: {e}")
            return None

    def _get_days_since(self, date_str: str) -> int:
        """Calculate days since a given date"""
        try:
            if not date_str:
                return 0
            if isinstance(date_str, str):
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                date_obj = date_str

            now = datetime.now(date_obj.tzinfo if hasattr(date_obj, 'tzinfo') else None)
            delta = now - date_obj
            return delta.days
        except Exception:
            return 0

    # ============================================
    # PARTNER MESSAGING METHODS
    # ============================================

    def get_or_create_partner_conversation(self, relationship_id: str) -> Dict[str, Any]:
        """Get existing conversation or create new one for relationship."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Try to get existing
                    cursor.execute("""
                        SELECT id, relationship_id, created_at, last_message_at,
                               last_message_preview, message_count
                        FROM partner_conversations
                        WHERE relationship_id = %s
                    """, (relationship_id,))

                    row = cursor.fetchone()
                    if row:
                        return {
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]),
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
                            "last_message_preview": row["last_message_preview"],
                            "message_count": row["message_count"] or 0
                        }

                    # Create new
                    cursor.execute("""
                        INSERT INTO partner_conversations (relationship_id)
                        VALUES (%s)
                        RETURNING id, relationship_id, created_at
                    """, (relationship_id,))

                    row = cursor.fetchone()
                    conn.commit()

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "last_message_at": None,
                        "last_message_preview": None,
                        "message_count": 0
                    }
        except Exception as e:
            print(f"Error getting/creating partner conversation: {e}")
            raise e

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by its ID."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, created_at, last_message_at,
                               last_message_preview, message_count
                        FROM partner_conversations
                        WHERE id = %s
                    """, (conversation_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
                        "last_message_preview": row["last_message_preview"],
                        "message_count": row["message_count"] or 0
                    }
        except Exception as e:
            print(f"Error getting conversation by ID: {e}")
            return None

    def save_partner_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        original_content: str = None,
        luna_intervened: bool = False,
        intervention_type: str = None
    ) -> Dict[str, Any]:
        """Save a new partner message."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO partner_messages
                            (conversation_id, sender_id, content, original_content,
                             luna_intervened, intervention_type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, conversation_id, sender_id, content, status,
                                  sent_at, luna_intervened, original_content
                    """, (
                        conversation_id, sender_id, content, original_content,
                        luna_intervened, intervention_type
                    ))

                    row = cursor.fetchone()
                    conn.commit()

                    return {
                        "id": str(row["id"]),
                        "conversation_id": str(row["conversation_id"]),
                        "sender_id": row["sender_id"],
                        "content": row["content"],
                        "status": row["status"],
                        "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                        "luna_intervened": row["luna_intervened"],
                        "original_content": row["original_content"]
                    }
        except Exception as e:
            print(f"Error saving partner message: {e}")
            raise e

    def get_partner_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        before_timestamp: str = None
    ) -> List[Dict[str, Any]]:
        """Get paginated messages for a conversation."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if before_timestamp:
                        cursor.execute("""
                            SELECT id, conversation_id, sender_id, content, status,
                                   sent_at, delivered_at, read_at, sentiment_label,
                                   emotions, escalation_risk, luna_intervened
                            FROM partner_messages
                            WHERE conversation_id = %s
                              AND sent_at < %s
                              AND deleted_at IS NULL
                            ORDER BY sent_at DESC
                            LIMIT %s
                        """, (conversation_id, before_timestamp, limit))
                    else:
                        cursor.execute("""
                            SELECT id, conversation_id, sender_id, content, status,
                                   sent_at, delivered_at, read_at, sentiment_label,
                                   emotions, escalation_risk, luna_intervened
                            FROM partner_messages
                            WHERE conversation_id = %s
                              AND deleted_at IS NULL
                            ORDER BY sent_at DESC
                            LIMIT %s
                        """, (conversation_id, limit))

                    rows = cursor.fetchall()

                    messages = []
                    for row in rows:
                        messages.append({
                            "id": str(row["id"]),
                            "conversation_id": str(row["conversation_id"]),
                            "sender_id": row["sender_id"],
                            "content": row["content"],
                            "status": row["status"],
                            "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                            "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
                            "read_at": row["read_at"].isoformat() if row["read_at"] else None,
                            "sentiment_label": row["sentiment_label"],
                            "emotions": row["emotions"] or [],
                            "escalation_risk": row["escalation_risk"],
                            "luna_intervened": row["luna_intervened"]
                        })

                    # Return in chronological order
                    return list(reversed(messages))
        except Exception as e:
            print(f"Error getting partner messages: {e}")
            return []

    def get_partner_chat_context_for_luna(
        self,
        relationship_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get partner chat history formatted for Luna's context.
        Returns messages with partner names for better AI understanding.
        """
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get conversation for this relationship
                    cursor.execute("""
                        SELECT id FROM partner_conversations
                        WHERE relationship_id = %s
                    """, (relationship_id,))
                    conv_row = cursor.fetchone()

                    if not conv_row:
                        return {
                            "relationship_id": relationship_id,
                            "message_count": 0,
                            "messages": [],
                            "summary": "No partner chat history available."
                        }

                    conversation_id = conv_row["id"]

                    # Get messages with all analysis fields
                    cursor.execute("""
                        SELECT sender_id, content, sent_at,
                               sentiment_label, emotions, escalation_risk,
                               luna_intervened, original_content
                        FROM partner_messages
                        WHERE conversation_id = %s
                          AND deleted_at IS NULL
                        ORDER BY sent_at ASC
                        LIMIT %s
                    """, (conversation_id, limit))

                    rows = cursor.fetchall()

                    messages = []
                    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
                    escalation_events = []

                    for row in rows:
                        msg = {
                            "sender": row["sender_id"],
                            "content": row["content"],
                            "timestamp": row["sent_at"].isoformat() if row["sent_at"] else None,
                            "sentiment": row["sentiment_label"],
                            "emotions": row["emotions"] or [],
                            "escalation_risk": row["escalation_risk"],
                            "luna_helped": row["luna_intervened"]
                        }
                        messages.append(msg)

                        # Track sentiment distribution
                        if row["sentiment_label"] and row["sentiment_label"] in sentiment_counts:
                            sentiment_counts[row["sentiment_label"]] += 1

                        # Track escalation events
                        if row["escalation_risk"] in ["high", "critical"]:
                            escalation_events.append({
                                "sender": row["sender_id"],
                                "timestamp": row["sent_at"].isoformat() if row["sent_at"] else None,
                                "risk_level": row["escalation_risk"]
                            })

                    # Generate summary for Luna
                    total = len(messages)
                    summary_parts = [f"Chat history contains {total} messages."]

                    if total > 0:
                        partner_a_count = len([m for m in messages if m["sender"] == "partner_a"])
                        partner_b_count = total - partner_a_count
                        summary_parts.append(f"Partner A sent {partner_a_count}, Partner B sent {partner_b_count}.")

                        if sentiment_counts["negative"] > 0:
                            summary_parts.append(f"{sentiment_counts['negative']} messages had negative sentiment.")

                        if escalation_events:
                            summary_parts.append(f"{len(escalation_events)} high-risk escalation moments detected.")

                    return {
                        "relationship_id": relationship_id,
                        "conversation_id": str(conversation_id),
                        "message_count": total,
                        "messages": messages,
                        "sentiment_distribution": sentiment_counts,
                        "escalation_events": escalation_events,
                        "summary": " ".join(summary_parts)
                    }

        except Exception as e:
            print(f"Error getting partner chat context for Luna: {e}")
            return {
                "relationship_id": relationship_id,
                "message_count": 0,
                "messages": [],
                "summary": "Error retrieving chat history."
            }

    def update_message_status(
        self,
        message_id: str,
        status: str,
        timestamp_field: str = None
    ) -> bool:
        """Update message status (delivered, read)."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if timestamp_field:
                        cursor.execute(f"""
                            UPDATE partner_messages
                            SET status = %s, {timestamp_field} = NOW()
                            WHERE id = %s
                        """, (status, message_id))
                    else:
                        cursor.execute("""
                            UPDATE partner_messages
                            SET status = %s
                            WHERE id = %s
                        """, (status, message_id))

                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating message status: {e}")
            return False

    def get_messaging_preferences(
        self,
        relationship_id: str,
        partner_id: str
    ) -> Dict[str, Any]:
        """Get messaging preferences for a partner, creating defaults if none exist."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Try to get existing
                    cursor.execute("""
                        SELECT id, relationship_id, partner_id,
                               luna_assistance_enabled, suggestion_mode,
                               intervention_enabled, intervention_sensitivity,
                               push_notifications_enabled, notification_sound,
                               show_sentiment_indicators, show_read_receipts,
                               show_typing_indicators, demo_mode_enabled,
                               created_at, updated_at
                        FROM partner_messaging_preferences
                        WHERE relationship_id = %s AND partner_id = %s
                    """, (relationship_id, partner_id))

                    row = cursor.fetchone()
                    if row:
                        return {
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]),
                            "partner_id": row["partner_id"],
                            "luna_assistance_enabled": row["luna_assistance_enabled"],
                            "suggestion_mode": row["suggestion_mode"],
                            "intervention_enabled": row["intervention_enabled"],
                            "intervention_sensitivity": row["intervention_sensitivity"],
                            "push_notifications_enabled": row["push_notifications_enabled"],
                            "notification_sound": row["notification_sound"],
                            "show_sentiment_indicators": row["show_sentiment_indicators"],
                            "show_read_receipts": row["show_read_receipts"],
                            "show_typing_indicators": row["show_typing_indicators"],
                            "demo_mode_enabled": row["demo_mode_enabled"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                        }

                    # Create defaults
                    cursor.execute("""
                        INSERT INTO partner_messaging_preferences
                            (relationship_id, partner_id)
                        VALUES (%s, %s)
                        RETURNING id, relationship_id, partner_id,
                                  luna_assistance_enabled, suggestion_mode,
                                  intervention_enabled, intervention_sensitivity,
                                  push_notifications_enabled, notification_sound,
                                  show_sentiment_indicators, show_read_receipts,
                                  show_typing_indicators, demo_mode_enabled
                    """, (relationship_id, partner_id))

                    row = cursor.fetchone()
                    conn.commit()

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "partner_id": row["partner_id"],
                        "luna_assistance_enabled": row["luna_assistance_enabled"],
                        "suggestion_mode": row["suggestion_mode"],
                        "intervention_enabled": row["intervention_enabled"],
                        "intervention_sensitivity": row["intervention_sensitivity"],
                        "push_notifications_enabled": row["push_notifications_enabled"],
                        "notification_sound": row["notification_sound"],
                        "show_sentiment_indicators": row["show_sentiment_indicators"],
                        "show_read_receipts": row["show_read_receipts"],
                        "show_typing_indicators": row["show_typing_indicators"],
                        "demo_mode_enabled": row["demo_mode_enabled"],
                        "created_at": None,
                        "updated_at": None
                    }
        except Exception as e:
            print(f"Error getting messaging preferences: {e}")
            raise e

    def update_messaging_preferences(
        self,
        relationship_id: str,
        partner_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update messaging preferences for a partner."""
        try:
            # Filter out None values and build dynamic SET clause
            valid_fields = [
                'luna_assistance_enabled', 'suggestion_mode',
                'intervention_enabled', 'intervention_sensitivity',
                'push_notifications_enabled', 'notification_sound',
                'show_sentiment_indicators', 'show_read_receipts',
                'show_typing_indicators', 'demo_mode_enabled'
            ]

            filtered_updates = {
                k: v for k, v in updates.items()
                if k in valid_fields and v is not None
            }

            if not filtered_updates:
                # No updates, just return current preferences
                return self.get_messaging_preferences(relationship_id, partner_id)

            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build the SET clause dynamically
                    set_parts = [f"{key} = %s" for key in filtered_updates.keys()]
                    set_clause = ", ".join(set_parts)
                    values = list(filtered_updates.values())

                    cursor.execute(f"""
                        UPDATE partner_messaging_preferences
                        SET {set_clause}, updated_at = NOW()
                        WHERE relationship_id = %s AND partner_id = %s
                        RETURNING id, relationship_id, partner_id,
                                  luna_assistance_enabled, suggestion_mode,
                                  intervention_enabled, intervention_sensitivity,
                                  push_notifications_enabled, notification_sound,
                                  show_sentiment_indicators, show_read_receipts,
                                  show_typing_indicators, demo_mode_enabled,
                                  created_at, updated_at
                    """, (*values, relationship_id, partner_id))

                    row = cursor.fetchone()

                    if not row:
                        # Preferences don't exist yet, create them first
                        self.get_messaging_preferences(relationship_id, partner_id)
                        # Then update
                        cursor.execute(f"""
                            UPDATE partner_messaging_preferences
                            SET {set_clause}, updated_at = NOW()
                            WHERE relationship_id = %s AND partner_id = %s
                            RETURNING id, relationship_id, partner_id,
                                      luna_assistance_enabled, suggestion_mode,
                                      intervention_enabled, intervention_sensitivity,
                                      push_notifications_enabled, notification_sound,
                                      show_sentiment_indicators, show_read_receipts,
                                      show_typing_indicators, demo_mode_enabled,
                                      created_at, updated_at
                        """, (*values, relationship_id, partner_id))
                        row = cursor.fetchone()

                    conn.commit()

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "partner_id": row["partner_id"],
                        "luna_assistance_enabled": row["luna_assistance_enabled"],
                        "suggestion_mode": row["suggestion_mode"],
                        "intervention_enabled": row["intervention_enabled"],
                        "intervention_sensitivity": row["intervention_sensitivity"],
                        "push_notifications_enabled": row["push_notifications_enabled"],
                        "notification_sound": row["notification_sound"],
                        "show_sentiment_indicators": row["show_sentiment_indicators"],
                        "show_read_receipts": row["show_read_receipts"],
                        "demo_mode_enabled": row["demo_mode_enabled"],
                        "show_typing_indicators": row["show_typing_indicators"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                    }
        except Exception as e:
            print(f"Error updating messaging preferences: {e}")
            raise e

    # ============================================
    # MESSAGE SUGGESTION METHODS (Phase 3)
    # ============================================

    def save_message_suggestion(
        self,
        conversation_id: str,
        sender_id: str,
        original_message: str,
        risk_assessment: str,
        detected_issues: List[str],
        primary_suggestion: str,
        suggestion_rationale: str,
        alternatives: List[Dict],
        underlying_need: str = None,
        context_message_count: int = 0
    ) -> Optional[str]:
        """Save a Luna suggestion for a draft message."""
        try:
            import json
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO message_suggestions
                            (conversation_id, sender_id, original_message,
                             risk_assessment, detected_issues,
                             primary_suggestion, suggestion_rationale, alternatives,
                             underlying_need, context_message_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        conversation_id, sender_id, original_message,
                        risk_assessment, json.dumps(detected_issues),
                        primary_suggestion, suggestion_rationale, json.dumps(alternatives),
                        underlying_need, context_message_count
                    ))

                    row = cursor.fetchone()
                    conn.commit()
                    return str(row["id"])
        except Exception as e:
            print(f"Error saving message suggestion: {e}")
            return None

    def update_message_suggestion_response(
        self,
        suggestion_id: str,
        user_action: str,
        final_message_id: str = None,
        selected_alternative_index: int = None
    ) -> bool:
        """Update a suggestion with the user's response."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE message_suggestions
                        SET user_action = %s,
                            final_message_id = %s,
                            selected_alternative_index = %s,
                            responded_at = NOW()
                        WHERE id = %s
                    """, (user_action, final_message_id, selected_alternative_index, suggestion_id))

                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating message suggestion response: {e}")
            return False

    def get_suggestion_acceptance_rate(
        self,
        relationship_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get suggestion acceptance statistics for analytics."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE user_action = 'accepted') as accepted,
                            COUNT(*) FILTER (WHERE user_action = 'rejected') as rejected,
                            COUNT(*) FILTER (WHERE user_action = 'modified') as modified,
                            COUNT(*) FILTER (WHERE user_action = 'ignored') as ignored
                        FROM message_suggestions ms
                        JOIN partner_conversations pc ON ms.conversation_id = pc.id
                        WHERE pc.relationship_id = %s
                          AND ms.created_at > NOW() - INTERVAL '%s days'
                          AND ms.risk_assessment != 'safe'
                    """, (relationship_id, days))

                    row = cursor.fetchone()
                    total = row["total"] or 0

                    return {
                        "total_suggestions": total,
                        "accepted": row["accepted"] or 0,
                        "rejected": row["rejected"] or 0,
                        "modified": row["modified"] or 0,
                        "ignored": row["ignored"] or 0,
                        "acceptance_rate": (row["accepted"] or 0) / total if total > 0 else 0
                    }
        except Exception as e:
            print(f"Error getting suggestion acceptance rate: {e}")
            return {
                "total_suggestions": 0,
                "accepted": 0,
                "rejected": 0,
                "modified": 0,
                "ignored": 0,
                "acceptance_rate": 0
            }

    def get_partner_messages_for_baseline(
        self,
        conversation_id: str,
        sender_id: str,
        days: int = 30,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages for calculating baseline message characteristics."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, content, sent_at, sentiment_label
                        FROM partner_messages
                        WHERE conversation_id = %s
                          AND sender_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                        ORDER BY sent_at DESC
                        LIMIT %s
                    """, (conversation_id, sender_id, days, limit))

                    rows = cursor.fetchall()
                    return [
                        {
                            "id": str(row["id"]),
                            "content": row["content"],
                            "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                            "sentiment_label": row["sentiment_label"]
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error getting messages for baseline: {e}")
            return []

    # ============================================
    # PHASE 4: MESSAGE ANALYSIS METHODS
    # ============================================

    def update_partner_message_analysis(
        self,
        message_id: str,
        sentiment_score: float,
        sentiment_label: str,
        emotions: list,
        detected_triggers: list,
        escalation_risk: str,
        gottman_markers: dict
    ) -> bool:
        """Update a message with Phase 4 analysis results."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE partner_messages
                        SET sentiment_score = %s,
                            sentiment_label = %s,
                            emotions = %s,
                            detected_triggers = %s,
                            escalation_risk = %s,
                            gottman_markers = %s
                        WHERE id = %s
                    """, (
                        sentiment_score,
                        sentiment_label,
                        json.dumps(emotions),
                        json.dumps(detected_triggers),
                        escalation_risk,
                        json.dumps(gottman_markers),
                        message_id
                    ))

                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating message analysis: {e}")
            return False

    def get_messaging_analytics(
        self,
        relationship_id: str,
        days: int = 30
    ) -> dict:
        """Get messaging analytics for dashboard (Phase 4)."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get conversation ID
                    cursor.execute("""
                        SELECT id FROM partner_conversations
                        WHERE relationship_id = %s
                    """, (relationship_id,))
                    row = cursor.fetchone()
                    if not row:
                        return self._empty_messaging_analytics(days)

                    conversation_id = str(row["id"])

                    # Message counts and sentiment distribution
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_messages,
                            COUNT(*) FILTER (WHERE sender_id = 'partner_a') as partner_a_count,
                            COUNT(*) FILTER (WHERE sender_id = 'partner_b') as partner_b_count,
                            COUNT(*) FILTER (WHERE sentiment_label = 'positive') as positive_count,
                            COUNT(*) FILTER (WHERE sentiment_label = 'negative') as negative_count,
                            COUNT(*) FILTER (WHERE sentiment_label = 'neutral') as neutral_count,
                            COUNT(*) FILTER (WHERE escalation_risk IN ('high', 'critical')) as high_risk_count,
                            COUNT(*) FILTER (WHERE luna_intervened = true) as luna_intervened_count,
                            AVG(sentiment_score) FILTER (WHERE sentiment_score IS NOT NULL) as avg_sentiment
                        FROM partner_messages
                        WHERE conversation_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                    """, (conversation_id, days))

                    stats = cursor.fetchone()
                    total = stats["total_messages"] or 0

                    # Daily message trend
                    cursor.execute("""
                        SELECT
                            DATE(sent_at) as date,
                            COUNT(*) as message_count,
                            AVG(sentiment_score) as avg_sentiment
                        FROM partner_messages
                        WHERE conversation_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                        GROUP BY DATE(sent_at)
                        ORDER BY date
                    """, (conversation_id, days))

                    daily_trend = [
                        {
                            "date": row["date"].isoformat() if row["date"] else None,
                            "count": row["message_count"],
                            "avg_sentiment": float(row["avg_sentiment"]) if row["avg_sentiment"] else 0
                        }
                        for row in cursor.fetchall()
                    ]

                    # Most common emotions
                    cursor.execute("""
                        SELECT emotion, COUNT(*) as count
                        FROM partner_messages,
                             jsonb_array_elements_text(emotions) as emotion
                        WHERE conversation_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                        GROUP BY emotion
                        ORDER BY count DESC
                        LIMIT 10
                    """, (conversation_id, days))

                    top_emotions = [
                        {"emotion": row["emotion"], "count": row["count"]}
                        for row in cursor.fetchall()
                    ]

                    # Detected triggers from messages
                    cursor.execute("""
                        SELECT trigger_phrase, COUNT(*) as count
                        FROM partner_messages,
                             jsonb_array_elements_text(detected_triggers) as trigger_phrase
                        WHERE conversation_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                        GROUP BY trigger_phrase
                        ORDER BY count DESC
                        LIMIT 10
                    """, (conversation_id, days))

                    top_triggers = [
                        {"trigger": row["trigger_phrase"], "count": row["count"]}
                        for row in cursor.fetchall()
                    ]

                    # Gottman markers counts
                    cursor.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE gottman_markers->>'criticism' = 'true') as criticism,
                            COUNT(*) FILTER (WHERE gottman_markers->>'contempt' = 'true') as contempt,
                            COUNT(*) FILTER (WHERE gottman_markers->>'defensiveness' = 'true') as defensiveness,
                            COUNT(*) FILTER (WHERE gottman_markers->>'stonewalling' = 'true') as stonewalling
                        FROM partner_messages
                        WHERE conversation_id = %s
                          AND sent_at > NOW() - INTERVAL '%s days'
                          AND deleted_at IS NULL
                          AND gottman_markers IS NOT NULL
                    """, (conversation_id, days))

                    gottman = cursor.fetchone()

                    return {
                        "period_days": days,
                        "total_messages": total,
                        "messages_by_partner": {
                            "partner_a": stats["partner_a_count"] or 0,
                            "partner_b": stats["partner_b_count"] or 0
                        },
                        "sentiment_distribution": {
                            "positive": stats["positive_count"] or 0,
                            "negative": stats["negative_count"] or 0,
                            "neutral": stats["neutral_count"] or 0,
                            "positive_ratio": (stats["positive_count"] or 0) / total if total > 0 else 0
                        },
                        "average_sentiment": float(stats["avg_sentiment"]) if stats["avg_sentiment"] else 0,
                        "high_risk_messages": stats["high_risk_count"] or 0,
                        "luna_interventions": stats["luna_intervened_count"] or 0,
                        "daily_trend": daily_trend,
                        "top_emotions": top_emotions,
                        "top_triggers": top_triggers,
                        "gottman_markers": {
                            "criticism": gottman["criticism"] or 0,
                            "contempt": gottman["contempt"] or 0,
                            "defensiveness": gottman["defensiveness"] or 0,
                            "stonewalling": gottman["stonewalling"] or 0
                        }
                    }
        except Exception as e:
            print(f"Error getting messaging analytics: {e}")
            return self._empty_messaging_analytics(days)

    def _empty_messaging_analytics(self, days: int = 30) -> dict:
        """Return empty analytics structure."""
        return {
            "period_days": days,
            "total_messages": 0,
            "messages_by_partner": {"partner_a": 0, "partner_b": 0},
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0, "positive_ratio": 0},
            "average_sentiment": 0,
            "high_risk_messages": 0,
            "luna_interventions": 0,
            "daily_trend": [],
            "top_emotions": [],
            "top_triggers": [],
            "gottman_markers": {"criticism": 0, "contempt": 0, "defensiveness": 0, "stonewalling": 0}
        }

    def add_detected_trigger(
        self,
        relationship_id: str,
        trigger_phrase: str,
        source: str,
        detected_by: str
    ) -> None:
        """Add a newly detected trigger phrase from messaging."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Check if trigger_phrases table exists and has the right schema
                    cursor.execute("""
                        INSERT INTO trigger_phrases
                            (relationship_id, phrase, source, detected_by, occurrence_count, created_at)
                        VALUES (%s, %s, %s, %s, 1, NOW())
                        ON CONFLICT (relationship_id, phrase)
                        DO UPDATE SET
                            occurrence_count = trigger_phrases.occurrence_count + 1,
                            updated_at = NOW()
                    """, (relationship_id, trigger_phrase, source, detected_by))
                    conn.commit()
        except Exception as e:
            # Table might not exist or have different schema - that's ok
            print(f"Could not add trigger phrase (non-critical): {e}")

    def record_escalation_event(
        self,
        relationship_id: str,
        source: str,
        severity: str,
        context: str
    ) -> None:
        """Record an escalation event for pattern tracking."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO escalation_events
                            (relationship_id, source, severity, context, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (relationship_id, source, severity, context))
                    conn.commit()
        except Exception as e:
            # Table might not exist - that's ok, this is supplementary
            print(f"Could not record escalation event (non-critical): {e}")

    # ============================================
    # CONNECTION GESTURES METHODS
    # ============================================

    def save_gesture(
        self,
        relationship_id: str,
        gesture_type: str,
        sent_by: str,
        message: str = None,
        ai_generated: bool = False,
        ai_context_used: dict = None
    ) -> Dict[str, Any]:
        """Save a new connection gesture."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        INSERT INTO connection_gestures
                            (relationship_id, gesture_type, sent_by, message,
                             ai_generated, ai_context_used)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, relationship_id, gesture_type, sent_by,
                                  message, ai_generated, sent_at, delivered_at,
                                  acknowledged_at, acknowledged_by, response_gesture_id
                    """, (
                        relationship_id, gesture_type, sent_by, message,
                        ai_generated, json.dumps(ai_context_used or {})
                    ))

                    row = cursor.fetchone()
                    conn.commit()

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "gesture_type": row["gesture_type"],
                        "sent_by": row["sent_by"],
                        "message": row["message"],
                        "ai_generated": row["ai_generated"],
                        "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                        "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
                        "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None,
                        "acknowledged_by": row["acknowledged_by"],
                        "response_gesture_id": str(row["response_gesture_id"]) if row["response_gesture_id"] else None
                    }
        except Exception as e:
            print(f"Error saving gesture: {e}")
            raise e

    def mark_gesture_delivered(self, gesture_id: str) -> bool:
        """Mark a gesture as delivered."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE connection_gestures
                        SET delivered_at = NOW()
                        WHERE id = %s AND delivered_at IS NULL
                    """, (gesture_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error marking gesture delivered: {e}")
            return False

    def acknowledge_gesture(
        self,
        gesture_id: str,
        acknowledged_by: str,
        response_gesture_id: str = None
    ) -> bool:
        """Mark a gesture as acknowledged, optionally linking a response gesture."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE connection_gestures
                        SET acknowledged_at = NOW(),
                            acknowledged_by = %s,
                            response_gesture_id = %s
                        WHERE id = %s AND acknowledged_at IS NULL
                    """, (acknowledged_by, response_gesture_id, gesture_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error acknowledging gesture: {e}")
            return False

    def get_pending_gestures(
        self,
        relationship_id: str,
        partner_id: str
    ) -> List[Dict[str, Any]]:
        """Get all unacknowledged gestures sent TO a specific partner."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, gesture_type, sent_by,
                               message, ai_generated, sent_at, delivered_at
                        FROM connection_gestures
                        WHERE relationship_id = %s
                          AND sent_by != %s
                          AND acknowledged_at IS NULL
                        ORDER BY sent_at ASC
                    """, (relationship_id, partner_id))

                    gestures = []
                    for row in cursor.fetchall():
                        gestures.append({
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]),
                            "gesture_type": row["gesture_type"],
                            "sent_by": row["sent_by"],
                            "message": row["message"],
                            "ai_generated": row["ai_generated"],
                            "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                            "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None
                        })
                    return gestures
        except Exception as e:
            print(f"Error getting pending gestures: {e}")
            return []

    def get_gesture_by_id(self, gesture_id: str) -> Optional[Dict[str, Any]]:
        """Get a gesture by its ID."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, gesture_type, sent_by,
                               message, ai_generated, sent_at, delivered_at,
                               acknowledged_at, acknowledged_by, response_gesture_id
                        FROM connection_gestures
                        WHERE id = %s
                    """, (gesture_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "gesture_type": row["gesture_type"],
                        "sent_by": row["sent_by"],
                        "message": row["message"],
                        "ai_generated": row["ai_generated"],
                        "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                        "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
                        "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None,
                        "acknowledged_by": row["acknowledged_by"],
                        "response_gesture_id": str(row["response_gesture_id"]) if row["response_gesture_id"] else None
                    }
        except Exception as e:
            print(f"Error getting gesture: {e}")
            return None

    def get_recent_gestures(
        self,
        relationship_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent gestures for a relationship."""
        try:
            with self.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, relationship_id, gesture_type, sent_by,
                               message, ai_generated, sent_at, acknowledged_at
                        FROM connection_gestures
                        WHERE relationship_id = %s
                        ORDER BY sent_at DESC
                        LIMIT %s
                    """, (relationship_id, limit))

                    gestures = []
                    for row in cursor.fetchall():
                        gestures.append({
                            "id": str(row["id"]),
                            "relationship_id": str(row["relationship_id"]),
                            "gesture_type": row["gesture_type"],
                            "sent_by": row["sent_by"],
                            "message": row["message"],
                            "ai_generated": row["ai_generated"],
                            "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                            "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None
                        })
                    return gestures
        except Exception as e:
            print(f"Error getting recent gestures: {e}")
            return []


# Global singleton instance
try:
    db_service = DatabaseService()
except Exception as e:
    print(f"❌ Failed to initialize DatabaseService: {e}")
    db_service = None
