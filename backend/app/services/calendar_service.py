"""
Calendar service for managing relationship events, cycle predictions, and pattern analysis.
Provides chronological data from PostgreSQL + semantic insights via RAG.
"""
import logging
import time
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from statistics import mean, stdev
from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# Event type colors for UI
EVENT_COLORS = {
    "period_start": "#ec4899",      # Pink
    "period_end": "#ec4899",        # Pink
    "ovulation": "#f472b6",         # Light pink
    "fertile_start": "#f9a8d4",     # Very light pink
    "fertile_end": "#f9a8d4",       # Very light pink
    "pms_start": "#fda4af",         # Rose
    "intimacy": "#3b82f6",          # Blue
    "conflict": "#dc2626",          # Red
    "anniversary": "#f59e0b",       # Gold/Amber
    "birthday": "#8b5cf6",          # Purple
    "first_date": "#ec4899",        # Pink
    "milestone": "#10b981",         # Green
    "custom": "#6b7280",            # Gray
}

# Default cycle parameters (can be personalized per user)
DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5
DEFAULT_OVULATION_DAY = 14  # Day 14 of cycle
DEFAULT_FERTILE_WINDOW_START = 10  # Days 10-16 typically fertile
DEFAULT_FERTILE_WINDOW_END = 16
DEFAULT_PMS_START_DAY = 21  # PMS typically starts day 21-28


class CalendarService:
    """Service for calendar operations, cycle predictions, and pattern analysis."""
    
    def __init__(self):
        self.db = db_service
        # Cache for calendar insights (5-minute TTL)
        self._insights_cache = {}  # {relationship_id: (insights_string, timestamp)}
    
    # =========================================================================
    # CYCLE EVENT MANAGEMENT
    # =========================================================================
    
    def create_cycle_event(
        self,
        partner_id: str,
        event_type: str,
        event_date: date,
        notes: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        cycle_day: Optional[int] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Optional[str]:
        """
        Create a cycle event (user-logged data only).
        
        Args:
            partner_id: "partner_a" or "partner_b"
            event_type: "period_start", "period_end", "symptom_log", "mood_log"
            event_date: The date of the event
            notes: Optional notes
            symptoms: Optional list of symptoms (e.g., ["cramps", "headache"])
            cycle_day: Day of cycle (auto-calculated if period_start)
            relationship_id: Relationship ID
        
        Returns:
            Event ID if created successfully
        """
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Check for existing event of same type on same date
                    cursor.execute("""
                        SELECT id FROM cycle_events 
                        WHERE partner_id = %s AND event_type = %s AND event_date = %s AND relationship_id = %s
                    """, (partner_id, event_type, event_date, relationship_id))
                    
                    existing = cursor.fetchone()
                    if existing:
                        logger.info(f"⚠️ Event already exists: {event_type} on {event_date}")
                        return str(existing[0])

                    # If this is a period_start, set cycle_day to 1
                    if event_type == "period_start":
                        cycle_day = 1  # First day of period is always day 1
                    
                    # Insert the event
                    cursor.execute("""
                        INSERT INTO cycle_events 
                        (relationship_id, partner_id, event_type, event_date, timestamp, notes, cycle_day, symptoms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (relationship_id, partner_id, event_type, event_date, datetime.now(), notes, cycle_day, symptoms))
                    
                    event_id = cursor.fetchone()[0]
                    conn.commit()
            
            logger.info(f"✅ Created cycle event: {event_type} on {event_date} for {partner_id}")
            return str(event_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating cycle event: {e}")
            return None

    def delete_event(self, event_id: str, event_type: str) -> bool:
        """Delete a calendar event by ID and type."""
        try:
            table_map = {
                "cycle": "cycle_events",
                "intimacy": "intimacy_events",
                "memorable": "memorable_dates",
                "conflict": "conflicts"
            }
            
            table = table_map.get(event_type)
            if not table:
                return False
                
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", (event_id,))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ Error deleting event: {e}")
            return False
    
    def get_cycle_events(
        self,
        partner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get cycle events for a partner within a date range."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Default to last 90 days if no dates specified
                    if not start_date:
                        start_date = date.today() - timedelta(days=90)
                    if not end_date:
                        end_date = date.today() + timedelta(days=30)
                    
                    cursor.execute("""
                        SELECT id, event_type, event_date, notes, cycle_day, timestamp
                        FROM cycle_events
                        WHERE partner_id = %s AND relationship_id = %s
                        AND event_date BETWEEN %s AND %s
                        ORDER BY event_date ASC;
                    """, (partner_id, relationship_id, start_date, end_date))
                    
                    events = []
                    for row in cursor.fetchall():
                        events.append({
                            "id": str(row[0]),
                            "type": "cycle",
                            "event_type": row[1],
                            "event_date": row[2].isoformat() if row[2] else None,
                            "title": self._get_cycle_event_title(row[1]),
                            "notes": row[3],
                            "cycle_day": row[4],
                            "color": EVENT_COLORS.get(row[1], "#ec4899"),
                            "logged_at": row[5].isoformat() if row[5] else None
                        })
                    
            return events
            
        except Exception as e:
            logger.error(f"❌ Error getting cycle events: {e}")
            return []
    
    def _get_cycle_event_title(self, event_type: str) -> str:
        """Get human-readable title for cycle event type."""
        titles = {
            "period_start": "Period Started",
            "period_end": "Period Ended",
            "ovulation": "Ovulation",
            "fertile_start": "Fertile Window Start",
            "fertile_end": "Fertile Window End",
            "pms_start": "PMS Phase",
        }
        return titles.get(event_type, event_type.replace("_", " ").title())
    
    # =========================================================================
    # CYCLE PREDICTIONS (Simple, Dynamic, 2 Months)
    # =========================================================================
    
    def get_cycle_predictions(
        self,
        partner_id: str,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """
        Generate simple cycle predictions for next 2 months based on historical data.
        Predictions are calculated dynamically (not stored in database).
        
        Args:
            partner_id: Partner to generate predictions for
            relationship_id: Relationship ID
        
        Returns:
            List of predicted cycle events for next 60 days
        """
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Get last 3 period_start events to calculate average cycle length
                    cursor.execute("""
                        SELECT event_date FROM cycle_events
                        WHERE partner_id = %s AND relationship_id = %s 
                        AND event_type = 'period_start'
                        ORDER BY event_date DESC
                        LIMIT 3;
                    """, (partner_id, relationship_id))
                    
                    period_dates = [row[0] for row in cursor.fetchall()]
            
            if len(period_dates) < 2:
                logger.info(f"Not enough period data for {partner_id} to predict")
                return []
            
            # Calculate average cycle length
            cycle_lengths = []
            for i in range(len(period_dates) - 1):
                cycle_length = (period_dates[i] - period_dates[i + 1]).days
                cycle_lengths.append(cycle_length)
            
            avg_cycle_length = round(mean(cycle_lengths)) if cycle_lengths else DEFAULT_CYCLE_LENGTH
            last_period = period_dates[0]
            
            logger.info(f"📊 Avg cycle length for {partner_id}: {avg_cycle_length} days")
            
            # Generate predictions for next 2 months only
            predictions = []
            current_date = last_period
            end_date = date.today() + timedelta(days=60)  # 2 months
            
            while current_date <= end_date:
                # Next period start
                next_period = current_date + timedelta(days=avg_cycle_length)
                
                if next_period > end_date:
                    break
                
                predictions.append({
                    "id": f"pred_{partner_id}_{next_period.isoformat()}",
                    "type": "prediction",
                    "event_type": "period_start",
                    "predicted_date": next_period.isoformat(),
                    "title": "Predicted Period",
                    "color": "#fda4af",  # Light pink
                    "is_prediction": True,
                    "cycle_length": avg_cycle_length
                })
                
                current_date = next_period
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Error generating predictions: {e}")
            return []
    
    # =========================================================================
    # CYCLE PHASE ANALYSIS (based on logged data only)
    # =========================================================================
    
    def get_current_cycle_phase(
        self,
        partner_id: str,
        target_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Dict[str, Any]:
        """
        Get the current cycle phase for a partner.
        
        Returns:
            Dict with phase info: phase_name, day_of_cycle, days_until_period, risk_level, etc.
        """
        if not target_date:
            target_date = date.today()
        
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Get most recent period starts to calculate cycle length
                    cursor.execute("""
                        SELECT event_date FROM cycle_events
                        WHERE partner_id = %s AND event_type = 'period_start' AND event_date <= %s
                        ORDER BY event_date DESC LIMIT 3;
                    """, (partner_id, target_date))
                    
                    period_dates = [row[0] for row in cursor.fetchall()]
            
            if not period_dates:
                return {
                    "phase_name": "Unknown",
                    "day_of_cycle": None,
                    "days_until_period": None,
                    "risk_level": "unknown",
                    "description": "Not enough cycle data to determine phase",
                    "confidence": 0.0
                }
            
            last_period_date = period_dates[0]
            
            # Calculate average cycle length from historical data
            cycle_length = DEFAULT_CYCLE_LENGTH
            if len(period_dates) >= 2:
                cycle_lengths = [(period_dates[i] - period_dates[i+1]).days for i in range(len(period_dates)-1)]
                cycle_length = round(sum(cycle_lengths) / len(cycle_lengths))
            
            # Calculate day of cycle
            day_of_cycle = (target_date - last_period_date).days + 1
            
            # Handle if we're past expected cycle length (period might be late)
            if day_of_cycle > cycle_length:
                return {
                    "phase_name": "Late Period",
                    "day_of_cycle": day_of_cycle,
                    "days_until_period": 0,
                    "days_late": day_of_cycle - cycle_length,
                    "risk_level": "high",
                    "description": f"Period is {day_of_cycle - cycle_length} days late. May be experiencing stress or hormonal changes.",
                    "confidence": 0.7
                }
            
            # Determine phase
            days_until_period = cycle_length - day_of_cycle
            
            if day_of_cycle <= DEFAULT_PERIOD_LENGTH:
                phase = {
                    "phase_name": "Menstruation",
                    "risk_level": "medium",
                    "description": "During period. May experience fatigue, cramps, mood changes.",
                    "emoji": "🩸"
                }
            elif day_of_cycle <= DEFAULT_FERTILE_WINDOW_START:
                phase = {
                    "phase_name": "Follicular",
                    "risk_level": "low",
                    "description": "Post-period phase. Energy typically increasing, mood stabilizing.",
                    "emoji": "🌱"
                }
            elif day_of_cycle <= DEFAULT_FERTILE_WINDOW_END:
                phase = {
                    "phase_name": "Ovulation",
                    "risk_level": "low",
                    "description": "Fertile window. Often highest energy and positive mood.",
                    "emoji": "✨"
                }
            elif day_of_cycle <= DEFAULT_PMS_START_DAY:
                phase = {
                    "phase_name": "Luteal (Early)",
                    "risk_level": "medium",
                    "description": "Post-ovulation. Energy may start declining.",
                    "emoji": "🍂"
                }
            else:
                phase = {
                    "phase_name": "Luteal (PMS)",
                    "risk_level": "high",
                    "description": "Pre-menstrual phase. May experience mood swings, irritability, sensitivity.",
                    "emoji": "⚠️"
                }
            
            return {
                **phase,
                "day_of_cycle": day_of_cycle,
                "days_until_period": days_until_period,
                "cycle_length": cycle_length,
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting cycle phase: {e}")
            return {
                "phase_name": "Unknown",
                "day_of_cycle": None,
                "risk_level": "unknown",
                "description": f"Error: {e}",
                "confidence": 0.0
            }
    
    # =========================================================================
    # MEMORABLE DATES
    # =========================================================================
    
    def create_memorable_date(
        self,
        title: str,
        event_date: date,
        event_type: str = "custom",
        description: Optional[str] = None,
        is_recurring: bool = True,
        reminder_days: int = 7,
        color_tag: Optional[str] = None,
        partner_id: Optional[str] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Optional[str]:
        """Create a memorable date (anniversary, birthday, milestone)."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if not color_tag:
                        color_tag = EVENT_COLORS.get(event_type, "#f59e0b")
                    
                    cursor.execute("""
                        INSERT INTO memorable_dates 
                        (relationship_id, event_type, title, description, event_date, is_recurring, 
                         reminder_days, color_tag, partner_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id;
                    """, (relationship_id, event_type, title, description, event_date, 
                          is_recurring, reminder_days, color_tag, partner_id))
                    
                    event_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"✅ Created memorable date: {title} on {event_date}")
                    return str(event_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating memorable date: {e}")
            if self.db.conn:
                self.db.conn.rollback()
            return None
    
    def get_memorable_dates(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_recurring: bool = True,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get memorable dates within a date range, including recurring events."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if not start_date:
                        start_date = date.today() - timedelta(days=30)
                    if not end_date:
                        end_date = date.today() + timedelta(days=365)
                    
                    # Get all memorable dates
                    cursor.execute("""
                        SELECT id, event_type, title, description, event_date, is_recurring, 
                               reminder_days, color_tag, partner_id
                        FROM memorable_dates
                        WHERE relationship_id = %s
                        ORDER BY event_date ASC;
                    """, (relationship_id,))
                    
                    events = []
                    current_year = date.today().year
                    
                    for row in cursor.fetchall():
                        event_id, event_type, title, description, event_date, is_recurring, \
                            reminder_days, color_tag, partner_id = row
                        
                        # For recurring events, generate instances for relevant years
                        if is_recurring and include_recurring:
                            # Check each year in range
                            for year in range(start_date.year, end_date.year + 1):
                                try:
                                    # Create date for this year
                                    yearly_date = event_date.replace(year=year)
                                    
                                    if start_date <= yearly_date <= end_date:
                                        years_since = year - event_date.year
                                        events.append({
                                            "id": str(event_id),
                                            "type": "memorable",
                                            "event_type": event_type,
                                            "title": f"{title}" + (f" ({years_since} years)" if years_since > 0 else ""),
                                            "description": description,
                                            "event_date": yearly_date.isoformat(),
                                            "original_date": event_date.isoformat(),
                                            "is_recurring": True,
                                            "years_since": years_since,
                                            "reminder_days": reminder_days,
                                            "color": color_tag or EVENT_COLORS.get(event_type, "#f59e0b"),
                                            "partner_id": partner_id
                                        })
                                except ValueError:
                                    # Handle Feb 29 on non-leap years
                                    pass
                        else:
                            # Non-recurring event
                            if start_date <= event_date <= end_date:
                                events.append({
                                    "id": str(event_id),
                                    "type": "memorable",
                                    "event_type": event_type,
                                    "title": title,
                                    "description": description,
                                    "event_date": event_date.isoformat(),
                                    "is_recurring": False,
                                    "color": color_tag or EVENT_COLORS.get(event_type, "#f59e0b"),
                                    "partner_id": partner_id
                                })
                    
                    # Sort by date
                    events.sort(key=lambda x: x["event_date"])
                    return events
            
        except Exception as e:
            logger.error(f"❌ Error getting memorable dates: {e}")
            return []
    
    def get_upcoming_events(
        self,
        days_ahead: int = 14,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID,
        partner_id: str = "partner_b"
    ) -> List[Dict[str, Any]]:
        """Get upcoming events (anniversaries, birthdays, predicted periods)."""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        events = []
        
        # Get memorable dates
        memorable = self.get_memorable_dates(today, end_date, relationship_id=relationship_id)
        events.extend(memorable)
        
        # Get cycle predictions (simple, next 2 months)
        predictions = self.get_cycle_predictions(partner_id, relationship_id)
        # Filter to days_ahead
        predictions = [p for p in predictions if p.get("predicted_date", "") <= end_date.isoformat()]
        events.extend(predictions)
        
        # Sort by date
        events.sort(key=lambda x: x.get("event_date") or x.get("predicted_date", ""))
        
        return events
    
    # =========================================================================
    # INTIMACY EVENTS
    # =========================================================================
    
    def create_intimacy_event(
        self,
        initiator_partner_id: Optional[str] = None,
        event_date: Optional[date] = None,
        notes: Optional[str] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Optional[str]:
        """Create an intimacy event."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if not event_date:
                        event_date = date.today()
                    
                    cursor.execute("""
                        INSERT INTO intimacy_events (relationship_id, timestamp, initiator_partner_id, metadata)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (relationship_id, datetime.combine(event_date, datetime.min.time()), 
                          initiator_partner_id, {"notes": notes} if notes else {}))
                    
                    event_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"✅ Created intimacy event on {event_date}")
                    return str(event_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating intimacy event: {e}")
            if self.db.conn:
                self.db.conn.rollback()
            return None
    
    def get_intimacy_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get intimacy events within a date range."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if not start_date:
                        start_date = date.today() - timedelta(days=90)
                    if not end_date:
                        end_date = date.today() + timedelta(days=1)
                    
                    cursor.execute("""
                        SELECT id, timestamp, initiator_partner_id, metadata
                        FROM intimacy_events
                        WHERE relationship_id = %s
                        AND timestamp BETWEEN %s AND %s
                        ORDER BY timestamp ASC;
                    """, (relationship_id, datetime.combine(start_date, datetime.min.time()),
                          datetime.combine(end_date, datetime.max.time())))
                    
                    events = []
                    for row in cursor.fetchall():
                        events.append({
                            "id": str(row[0]),
                            "type": "intimacy",
                            "event_type": "intimacy",
                            "event_date": row[1].date().isoformat() if row[1] else None,
                            "title": "💕 Intimacy",
                            "initiator": row[2],
                            "color": EVENT_COLORS["intimacy"],
                            "metadata": row[3] if row[3] else {}
                        })
                    
                    return events
            
        except Exception as e:
            logger.error(f"❌ Error getting intimacy events: {e}")
            return []
    
    # =========================================================================
    # CONFLICT EVENTS (from existing conflicts table)
    # =========================================================================
    
    def get_conflict_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get conflicts as calendar events."""
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    if not start_date:
                        start_date = date.today() - timedelta(days=90)
                    if not end_date:
                        end_date = date.today() + timedelta(days=1)
                    
                    cursor.execute("""
                        SELECT id, started_at, ended_at, status, metadata, title
                        FROM conflicts
                        WHERE relationship_id = %s
                        AND started_at BETWEEN %s AND %s
                        ORDER BY started_at ASC;
                    """, (relationship_id, datetime.combine(start_date, datetime.min.time()),
                          datetime.combine(end_date, datetime.max.time())))
                    
                    events = []
                    for row in cursor.fetchall():
                        # Use title from DB column, fallback to metadata, then default
                        db_title = row[5]
                        meta_title = (row[4] or {}).get("title")
                        display_title = db_title or meta_title or "⚠️ Conflict"
                        
                        events.append({
                            "id": str(row[0]),
                            "type": "conflict",
                            "event_type": "conflict",
                            "event_date": row[1].date().isoformat() if row[1] else None,
                            "title": display_title,
                            "started_at": row[1].isoformat() if row[1] else None,
                            "ended_at": row[2].isoformat() if row[2] else None,
                            "status": row[3],
                            "color": EVENT_COLORS["conflict"],
                            "metadata": row[4] if row[4] else {}
                        })
                    
                    return events
            
        except Exception as e:
            logger.error(f"❌ Error getting conflict events: {e}")
            return []

    def extract_and_store_conflict_topics(self, conflict_id: str) -> List[str]:
        """
        Extract topics from a conflict's mediator session and store in metadata.
        Returns the extracted topics.
        """
        try:
            # 1. Get mediator transcript
            transcript = ""
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Get session ID and content
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
                        messages = row[0] # JSONB list
                        # Format transcript
                        transcript_lines = []
                        for msg in messages:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            transcript_lines.append(f"{role}: {content}")
                        transcript = "\n".join(transcript_lines)
            
            if not transcript:
                logger.warning(f"⚠️ No transcript found for conflict {conflict_id}")
                return []

            # 2. Extract topics and generate title using LLM
            # Run in parallel if possible, but sequential is fine for now
            topics = llm_service.extract_topics(transcript)
            title = llm_service.generate_conflict_title(transcript)
            
            # 3. Update conflict metadata
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Fetch existing metadata first
                    cursor.execute("SELECT metadata FROM conflicts WHERE id = %s", (conflict_id,))
                    row = cursor.fetchone()
                    metadata = row[0] if row and row[0] else {}
                    
                    # Update metadata
                    metadata["topics"] = topics
                    metadata["title"] = title
                    
                    # Save back
                    cursor.execute("""
                        UPDATE conflicts 
                        SET metadata = %s 
                        WHERE id = %s
                    """, (json.dumps(metadata), conflict_id))
                    conn.commit()
            
            logger.info(f"✅ Analyzed conflict {conflict_id}: Title='{title}', Topics={topics}")
            return topics
            
        except Exception as e:
            logger.error(f"❌ Error extracting topics for conflict {conflict_id}: {e}")
            return []
    
    # =========================================================================
    # AGGREGATED CALENDAR VIEW
    # =========================================================================
    
    def get_calendar_events(
        self,
        year: int,
        month: int,
        filters: List[str] = None,
        include_predictions: bool = True,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID,
        partner_id: str = "partner_b"
    ) -> Dict[str, Any]:
        """
        Get all calendar events for a month (chronologically ordered).
        
        Args:
            year: Year
            month: Month (1-12)
            filters: List of event types to include (None = all)
            include_predictions: Whether to include cycle predictions
            relationship_id: Relationship ID
            partner_id: Partner ID for cycle predictions
        
        Returns:
            Dict with events grouped by date + summary stats
        """
        # Calculate date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Default filters
        if filters is None:
            filters = ["cycle", "intimacy", "conflict", "memorable", "prediction"]
        
        all_events = []
        
        # Fetch each event type
        if "cycle" in filters:
            cycle_events = self.get_cycle_events(partner_id, start_date, end_date, relationship_id)
            all_events.extend(cycle_events)
        
        if "intimacy" in filters:
            intimacy_events = self.get_intimacy_events(start_date, end_date, relationship_id)
            all_events.extend(intimacy_events)
        
        if "conflict" in filters:
            conflict_events = self.get_conflict_events(start_date, end_date, relationship_id)
            all_events.extend(conflict_events)
        
        if "memorable" in filters:
            memorable_dates = self.get_memorable_dates(start_date, end_date, True, relationship_id)
            all_events.extend(memorable_dates)
        
        if "prediction" in filters and include_predictions:
            # Get predictions and filter to this month
            predictions = self.get_cycle_predictions(partner_id, relationship_id)
            predictions = [p for p in predictions 
                          if start_date.isoformat() <= p.get("predicted_date", "") <= end_date.isoformat()]
            all_events.extend(predictions)
        
        # Sort by date
        all_events.sort(key=lambda x: x.get("event_date") or x.get("predicted_date", ""))
        
        # Group by date
        events_by_date = {}
        for event in all_events:
            event_date = event.get("event_date") or event.get("predicted_date")
            if event_date:
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)
        
        # Summary stats
        stats = {
            "total_events": len(all_events),
            "cycle_events": len([e for e in all_events if e.get("type") == "cycle"]),
            "predictions": len([e for e in all_events if e.get("is_prediction")]),
            "conflict_events": len([e for e in all_events if e.get("type") == "conflict"]),
            "intimacy_events": len([e for e in all_events if e.get("type") == "intimacy"]),
            "memorable_events": len([e for e in all_events if e.get("type") == "memorable"]),
        }
        
        return {
            "year": year,
            "month": month,
            "events": all_events,
            "events_by_date": events_by_date,
            "stats": stats
        }
    
    # =========================================================================
    # PATTERN ANALYSIS & INSIGHTS
    # =========================================================================
    
    def get_conflict_cycle_correlation(
        self,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID,
        lookback_days: int = 180,
        prefetched_conflicts: Optional[List[Dict]] = None,
        prefetched_cycle_events: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze correlation between conflicts and cycle phases.
        OPTIMIZED: Accepts prefetched data to avoid N+1 queries.
        
        Returns:
            Dict with correlation stats and insights
        """
        try:
            # Use prefetched conflicts if available, otherwise fetch
            if prefetched_conflicts is not None:
                conflicts = prefetched_conflicts
            else:
                conflicts = self.get_conflict_events(
                    date.today() - timedelta(days=lookback_days),
                    date.today(),
                    relationship_id
                )
            
            if not conflicts:
                return {
                    "has_data": False,
                    "message": "Not enough conflict data for analysis"
                }
            
            # Helper to get phase from prefetched events (avoiding DB calls)
            def get_phase_for_date(target_date: date, cycle_evts: List[Dict]) -> str:
                # Simple approximation based on last period
                # Find the most recent period_start before target_date
                last_period = None
                for evt in sorted(cycle_evts, key=lambda x: x['event_date'], reverse=True):
                    if evt['event_type'] == 'period_start':
                        evt_date = date.fromisoformat(evt['event_date'])
                        if evt_date <= target_date:
                            last_period = evt_date
                            break
                
                if not last_period:
                    return "Unknown"
                
                day_of_cycle = (target_date - last_period).days + 1
                
                if day_of_cycle <= DEFAULT_PERIOD_LENGTH: return "Menstruation"
                if day_of_cycle <= DEFAULT_FERTILE_WINDOW_START: return "Follicular"
                if day_of_cycle <= DEFAULT_FERTILE_WINDOW_END: return "Ovulation"
                if day_of_cycle <= DEFAULT_PMS_START_DAY: return "Luteal (Early)"
                return "Luteal (PMS)"

            # Use prefetched cycle events if available
            cycle_events_list = []
            if prefetched_cycle_events is not None:
                cycle_events_list = prefetched_cycle_events
            else:
                # Fallback to fetching if not provided (slower)
                cycle_events_list = self.get_cycle_events(
                    "partner_b", 
                    date.today() - timedelta(days=lookback_days + 30), # Extra buffer
                    date.today(), 
                    relationship_id
                )

            # For each conflict, determine what cycle phase Elara was in
            phase_counts = {
                "Menstruation": 0,
                "Follicular": 0,
                "Ovulation": 0,
                "Luteal (Early)": 0,
                "Luteal (PMS)": 0,
                "Unknown": 0
            }
            
            for conflict in conflicts:
                conflict_date_str = conflict.get("event_date")
                if conflict_date_str:
                    conflict_date = date.fromisoformat(conflict_date_str)
                    
                    # Use in-memory lookup if we have cycle events
                    if cycle_events_list:
                        phase_name = get_phase_for_date(conflict_date, cycle_events_list)
                    else:
                        # Fallback to slow DB call (should be avoided)
                        phase = self.get_current_cycle_phase("partner_b", conflict_date, relationship_id)
                        phase_name = phase.get("phase_name", "Unknown")
                        
                    if phase_name in phase_counts:
                        phase_counts[phase_name] += 1
                    else:
                        phase_counts["Unknown"] += 1
            
            total_conflicts = sum(phase_counts.values())
            
            # Calculate percentages
            phase_percentages = {
                phase: (count / total_conflicts * 100) if total_conflicts > 0 else 0
                for phase, count in phase_counts.items()
            }
            
            # Identify high-risk phases (significantly above average)
            # Average would be ~20% per phase (5 phases)
            high_risk_phases = [
                phase for phase, pct in phase_percentages.items()
                if pct > 25 and phase != "Unknown"
            ]
            
            # Generate insight
            insight = ""
            pms_pct = phase_percentages.get("Luteal (PMS)", 0)
            menstruation_pct = phase_percentages.get("Menstruation", 0)
            
            if pms_pct + menstruation_pct > 50:
                insight = f"⚠️ {pms_pct + menstruation_pct:.0f}% of conflicts occur during PMS or menstruation phases. Consider being extra patient during these times."
            elif high_risk_phases:
                insight = f"📊 Higher conflict frequency during: {', '.join(high_risk_phases)}"
            else:
                insight = "✅ Conflicts are evenly distributed across cycle phases - no strong correlation detected."
            
            return {
                "has_data": True,
                "total_conflicts": total_conflicts,
                "lookback_days": lookback_days,
                "phase_counts": phase_counts,
                "phase_percentages": phase_percentages,
                "high_risk_phases": high_risk_phases,
                "insight": insight
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing conflict-cycle correlation: {e}")
            return {
                "has_data": False,
                "error": str(e)
            }
    
    def get_calendar_insights_for_llm(
        self,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> str:
        """
        Generate a formatted calendar insights string for injection into LLM context.
        Uses tiered retrieval: relationship history + milestones + recent events + cycle phase.
        
        OPTIMIZED: Caches results for 5 minutes to prevent repeated slow queries.
        
        Returns:
            Formatted string with comprehensive but token-efficient relationship context
        """
        # Check cache first (5-minute TTL)
        cache_key = relationship_id
        if cache_key in self._insights_cache:
            cached_insights, cached_time = self._insights_cache[cache_key]
            age = time.time() - cached_time
            if age < 300:  # 5 minutes
                logger.info(f"✅ Calendar insights from cache (age: {age:.1f}s)")
                return cached_insights
        
        # Generate fresh insights
        logger.info(f"🔄 Generating fresh calendar insights (cache miss or expired)")
        insights = self._generate_calendar_insights(relationship_id)
        
        # Cache for 5 minutes
        self._insights_cache[cache_key] = (insights, time.time())
        
        return insights
    
    def _generate_calendar_insights(self, relationship_id: str) -> str:
        """Internal method to generate calendar insights (called when cache misses)"""
        insights = []
        
        # =========================================================================
        # TIER 1: Relationship History (Always Include) ~50 tokens
        # =========================================================================
        try:
            with self.db.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Get relationship start date
                    cursor.execute("""
                        SELECT created_at FROM relationships
                        WHERE id = %s;
                    """, (relationship_id,))
                    
                    rel_result = cursor.fetchone()
                    if rel_result:
                        start_date = rel_result[0]
                        duration_days = (datetime.now().date() - start_date.date()).days
                        duration_months = duration_days // 30
                        insights.append("📖 RELATIONSHIP HISTORY")
                        insights.append(f"   Together since: {start_date.strftime('%B %d, %Y')} ({duration_months} months)")
        except Exception as e:
            logger.error(f"Error fetching relationship history: {e}")
        
        # =========================================================================
        # TIER 2: Milestone Events (Top 5) ~100 tokens
        # =========================================================================
        try:
            milestones = self.get_memorable_dates(
                start_date=None,
                end_date=None,
                include_recurring=True,
                relationship_id=relationship_id
            )
            
            # Filter for milestone types and sort by importance
            priority_types = ['anniversary', 'first_date', 'milestone', 'birthday']
            milestone_events = [m for m in milestones if m.get('event_type') in priority_types]
            milestone_events.sort(key=lambda x: priority_types.index(x.get('event_type', 'custom')))
            
            if milestone_events:
                insights.append("   Key moments:")
                for event in milestone_events[:5]:  # Limit to 5
                    title = event.get('title', 'Event')
                    event_date = event.get('event_date', '')
                    event_type = event.get('event_type', 'event')
                    
                    # Format date nicely
                    if event_date:
                        try:
                            date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
                            days_ago = (datetime.now().date() - date_obj).days
                            
                            if days_ago < 0:
                                time_ref = "upcoming"
                            elif days_ago == 0:
                                time_ref = "today"
                            elif days_ago < 30:
                                time_ref = f"{days_ago} days ago"
                            elif days_ago < 365:
                                time_ref = f"{days_ago // 30} months ago"
                            else:
                                time_ref = f"{days_ago // 365} years ago"
                            
                            insights.append(f"      • {title} ({time_ref})")
                        except:
                            insights.append(f"      • {title}")
                insights.append("")
        except Exception as e:
            logger.error(f"Error fetching milestones: {e}")
        
        # =========================================================================
        # TIER 3: Recent Events (Last 30 days) ~50 tokens
        # =========================================================================
        try:
            recent_start = datetime.now().date() - timedelta(days=30)
            
            # Recent memorable dates
            recent_memorable = self.get_memorable_dates(
                start_date=recent_start,
                end_date=datetime.now().date(),
                include_recurring=False,
                relationship_id=relationship_id
            )
            
            # Recent intimacy events
            recent_intimacy = self.get_intimacy_events(
                start_date=recent_start,
                end_date=datetime.now().date(),
                relationship_id=relationship_id
            )
            
            recent_items = []
            if recent_memorable:
                recent_items.append(f"{len(recent_memorable)} special moments")
            if recent_intimacy:
                recent_items.append(f"{len(recent_intimacy)} intimacy events")
            
            if recent_items:
                insights.append("📅 RECENT ACTIVITY (Last 30 Days)")
                insights.append(f"   {', '.join(recent_items)}")
                insights.append("")
        except Exception as e:
            logger.error(f"Error fetching recent events: {e}")
        
        # =========================================================================
        # Current Cycle Phase (Existing)
        # =========================================================================
        phase = self.get_current_cycle_phase("partner_b", relationship_id=relationship_id)
        if phase.get("phase_name") != "Unknown":
            phase_emoji = phase.get("emoji", "📅")
            insights.append(f"🩸 CURRENT CYCLE PHASE (Elara)")
            insights.append(f"   {phase_emoji} Phase: {phase.get('phase_name')}")
            insights.append(f"   Day of cycle: {phase.get('day_of_cycle', 'N/A')}")
            insights.append(f"   Days until period: {phase.get('days_until_period', 'N/A')}")
            insights.append(f"   Risk level: {phase.get('risk_level', 'unknown').upper()}")
            insights.append(f"   Note: {phase.get('description', '')}")
            insights.append("")
        
        # =========================================================================
        # Upcoming Events (Existing)
        # =========================================================================
        upcoming = self.get_upcoming_events(14, relationship_id)
        if upcoming:
            insights.append("📌 UPCOMING EVENTS (Next 14 Days)")
            for event in upcoming[:5]:  # Limit to 5
                event_date = event.get("event_date") or event.get("predicted_date")
                title = event.get("title", "Event")
                confidence = event.get("confidence")
                if confidence:
                    insights.append(f"   • {event_date}: {title} (confidence: {confidence:.0%})")
                else:
                    insights.append(f"   • {event_date}: {title}")
            insights.append("")
        
        # =========================================================================
        # Conflict Pattern Insights (Existing)
        # =========================================================================
        correlation = self.get_conflict_cycle_correlation(relationship_id)
        if correlation.get("has_data"):
            insights.append("📊 CONFLICT PATTERN INSIGHT")
            insights.append(f"   {correlation.get('insight', 'No patterns detected')}")
            insights.append("")
        
        # =========================================================================
        # Risk Assessment (Existing)
        # =========================================================================
        if phase.get("risk_level") == "high":
            insights.append("⚠️ TODAY'S RISK ASSESSMENT: HIGH")
            insights.append("   Elara may be in a sensitive phase. Recommend:")
            insights.append("   - Extra patience and empathy")
            insights.append("   - Avoid bringing up contentious topics")
            insights.append("   - Be supportive and understanding")
        elif phase.get("risk_level") == "medium":
            insights.append("📋 TODAY'S RISK ASSESSMENT: MEDIUM")
            insights.append("   Be mindful of emotional sensitivity.")
        
        return "\n".join(insights) if insights else "No calendar insights available."
    
    def get_conflict_memory_context(
        self,
        current_topic: str,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> str:
        """
        Get formatted context about similar past conflicts.
        Used to inject into Luna's knowledge during mediation.
        
        Args:
            current_topic: What the user is currently discussing
            relationship_id: Relationship filter
            
        Returns:
            Formatted string for LLM context
        """
        from app.services.pinecone_service import pinecone_service
        
        try:
            similar = pinecone_service.search_similar_conflicts(
                query_text=current_topic,
                relationship_id=relationship_id,
                top_k=2  # Just top 2 most relevant
            )
            
            if not similar:
                return ""
            
            context_lines = ["📚 SIMILAR PAST CONFLICTS"]
            for idx, conflict in enumerate(similar, 1):
                date_str = conflict["date"][:10] if conflict["date"] != "Unknown" else "Recently"
                context_lines.append(
                    f"   {idx}. {date_str}: {conflict['summary']}"
                )
                if conflict.get("root_causes"):
                    causes_str = conflict["root_causes"]
                    # Parse if it's a string representation of a list
                    if isinstance(causes_str, str) and causes_str.startswith("["):
                        import ast
                        try:
                            causes_list = ast.literal_eval(causes_str)
                            if causes_list:
                                context_lines.append(f"      Root cause: {causes_list[0]}")
                        except:
                            pass
                    elif isinstance(causes_str, list) and causes_str:
                        context_lines.append(f"      Root cause: {causes_str[0]}")
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Error retrieving conflict memory: {e}")
            return ""


    def get_analytics_dashboard_data(
        self,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID,
        partner_id: str = "partner_b"
    ) -> Dict[str, Any]:
        """
        Get aggregated data for the analytics dashboard.
        Includes health score, trends, cycle correlation, and insights.
        """
        try:
            today = date.today()
            last_30_days = today - timedelta(days=30)
            
            # 1. Fetch Raw Data (Last 30 Days)
            conflicts = self.get_conflict_events(last_30_days, today, relationship_id)
            intimacy = self.get_intimacy_events(last_30_days, today, relationship_id)
            cycle_phase = self.get_current_cycle_phase(partner_id, today, relationship_id)
            
            # 2. Calculate Relationship Health Score (0-100)
            # Base score: 70
            # +5 per intimacy event (max +30)
            # -5 per unresolved conflict (was -10)
            # -2 per resolved conflict (was -5)
            # +10 if no conflicts in last 14 days
            
            health_score = 70
            
            # Intimacy boost
            intimacy_count = len(intimacy)
            health_score += min(intimacy_count * 5, 30)
            
            # Conflict penalty
            conflict_count = len(conflicts)
            
            # FIX: Treat 'completed' as 'resolved' along with 'resolved'
            resolved_conflicts = [c for c in conflicts if c.get("status") in ["resolved", "completed"]]
            resolved_count = len(resolved_conflicts)
            unresolved_count = conflict_count - resolved_count
            
            # Cap max penalty to avoid 0 score for active users
            penalty = (unresolved_count * 5) + (resolved_count * 2)
            penalty = min(penalty, 60) # Max penalty 60 points
            
            health_score -= penalty
            
            # Conflict-free bonus
            recent_conflicts = [c for c in conflicts if c.get("started_at") and date.fromisoformat(c["started_at"][:10]) > (today - timedelta(days=14))]
            if not recent_conflicts:
                health_score += 10
            
            # Clamp score 10-100 (never show 0 unless something is really wrong)
            health_score = max(10, min(100, health_score))
            
            # Determine trend (vs previous 30 days - simplified for now)
            # For MVP, we'll just use a heuristic based on current score
            trend = "stable"
            if health_score > 80: trend = "improving"
            elif health_score < 50: trend = "declining"
            
            # 3. Weekly Trends (Last 4 Weeks)
            weeks = []
            for i in range(4):
                week_start = today - timedelta(days=(3 - i) * 7 + 6)
                week_end = week_start + timedelta(days=6)
                week_label = f"Week {i+1}"
                
                # Count events in this week
                w_conflicts = 0
                w_intimacy = 0
                
                for c in conflicts:
                    c_date = date.fromisoformat(c["event_date"])
                    if week_start <= c_date <= week_end:
                        w_conflicts += 1
                        
                for i_evt in intimacy:
                    i_date = date.fromisoformat(i_evt["event_date"])
                    if week_start <= i_date <= week_end:
                        w_intimacy += 1
                
                weeks.append({
                    "name": week_label,
                    "conflicts": w_conflicts,
                    "intimacy": w_intimacy,
                    "date_start": week_start.isoformat(),
                    "date_end": week_end.isoformat()
                })
            
            # 4. Cycle Correlation (Heatmap Data)
            # Fetch long-term history for correlation
            history_start = today - timedelta(days=90)
            history_conflicts = self.get_conflict_events(history_start, today, relationship_id)
            
            # Pre-fetch cycle events for the same period to avoid N+1 queries
            history_cycle_events = self.get_cycle_events(partner_id, history_start - timedelta(days=40), today, relationship_id)
            
            # Use the optimized correlation method
            correlation_data = self.get_conflict_cycle_correlation(
                relationship_id, 
                lookback_days=90,
                prefetched_conflicts=history_conflicts,
                prefetched_cycle_events=history_cycle_events
            )
            
            # Generate heatmap data (Days 1-30)
            cycle_heatmap = [0] * 30
            
            # Helper to get day of cycle efficiently (with back-calculation)
            def get_day_of_cycle(target_date: date, cycle_evts: List[Dict]) -> Optional[int]:
                # 1. Try to find a preceding period
                last_period = None
                period_starts = [
                    date.fromisoformat(e['event_date']) 
                    for e in cycle_evts 
                    if e['event_type'] == 'period_start'
                ]
                period_starts.sort()
                
                # Find the latest period start <= target_date
                for p_date in reversed(period_starts):
                    if p_date <= target_date:
                        last_period = p_date
                        break
                
                if last_period:
                    return (target_date - last_period).days + 1
                
                # 2. If no preceding period, try to back-calculate from a future period
                # (Assuming regular 28-day cycle for estimation if no history)
                if period_starts:
                    first_future_period = period_starts[0] # Earliest known period
                    days_diff = (first_future_period - target_date).days
                    
                    # Estimate cycle length (use avg if available, else 28)
                    # Simple estimation: 28 days
                    cycle_len = 28 
                    
                    # Calculate how many cycles back
                    cycles_back = (days_diff // cycle_len) + 1
                    estimated_prev_period = first_future_period - timedelta(days=cycles_back * cycle_len)
                    
                    return (target_date - estimated_prev_period).days + 1
                    
                return None

            for c in history_conflicts:
                c_date = date.fromisoformat(c["event_date"])
                day = get_day_of_cycle(c_date, history_cycle_events)
                if day and 1 <= day <= 30:
                    cycle_heatmap[day-1] += 1
            
            # 5. Tension Forecast
            # Simple heuristic: High risk if in PMS (Luteal PMS) or if recent conflict trend is high
            tension_level = "Low"
            forecast_msg = "Conditions are favorable for connection."
            
            if cycle_phase.get("phase_name") == "Luteal (PMS)":
                tension_level = "High"
                forecast_msg = " PMS phase detected. Tension may be elevated."
            elif conflict_count > 3:
                tension_level = "Medium"
                forecast_msg = "Recent conflict frequency suggests underlying tension."
            
            # 6. Interaction Ratio (Gottman Ratio)
            # Ideal is 5:1 (5 positive for every 1 negative)
            ratio_val = 0
            if conflict_count > 0:
                ratio_val = round(intimacy_count / conflict_count, 1)
            else:
                ratio_val = intimacy_count if intimacy_count > 0 else 0 # Infinite/High if no conflicts
            
            ratio_status = "Healthy"
            if ratio_val >= 5: ratio_status = "Excellent"
            elif ratio_val >= 3: ratio_status = "Good"
            elif ratio_val >= 1: ratio_status = "Fair"
            else: ratio_status = "Critical"
            
            # 7. Top Conflict Topics (Top 5 most frequent)
            topic_counts = {}
            for c in conflicts:
                # Try to get AI-extracted topics from metadata first
                metadata = c.get("metadata", {})
                ai_topics = metadata.get("topics")
                
                if ai_topics and isinstance(ai_topics, list) and len(ai_topics) > 0:
                    for topic in ai_topics:
                        topic = topic.strip()
                        if topic:
                            topic_counts[topic] = topic_counts.get(topic, 0) + 1
                # else:
                #     # Fallback removed as per user request - only use AI topics
                #     pass
            
            # Sort by count and take top 5
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_topics_list = [{"topic": topic, "count": count} for topic, count in top_topics]

            return {
                "health_score": {
                    "value": health_score,
                    "trend": trend,
                    "status": "Excellent" if health_score > 80 else "Good" if health_score > 60 else "Needs Attention"
                },
                "trends": weeks,
                "cycle_correlation": cycle_heatmap,
                "tension_forecast": {
                    "level": tension_level,
                    "message": forecast_msg,
                    "next_high_risk_date": (today + timedelta(days=cycle_phase.get("days_until_period", 0) - 7)).isoformat() if cycle_phase.get("days_until_period") else None
                },
                "stats": {
                    "conflicts_30d": conflict_count,
                    "intimacy_30d": intimacy_count,
                    "unresolved": unresolved_count
                },
                "resolution_stats": {
                    "resolved": resolved_count,
                    "unresolved": unresolved_count,
                    "total": conflict_count,
                    "rate": round((resolved_count / conflict_count * 100) if conflict_count > 0 else 100)
                },
                "interaction_ratio": {
                    "value": ratio_val,
                    "target": 5.0,
                    "status": ratio_status
                },
                "top_topics": top_topics_list
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating analytics data: {e}")
            return {}


# Global instance
try:
    calendar_service = CalendarService()
except Exception as e:
    logger.error(f"❌ Failed to initialize CalendarService: {e}")
    calendar_service = None



