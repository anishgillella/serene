"""
Database service for direct PostgreSQL access (bypasses Supabase RLS)
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

class DatabaseService:
    """Service for direct database access"""
    
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        """Get database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(settings.DATABASE_URL)
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
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None

# Global instance
db_service = DatabaseService()



