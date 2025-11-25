"""
Calendar service for managing relationship events, cycle predictions, and pattern analysis.
Provides chronological data from PostgreSQL + semantic insights via RAG.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from statistics import mean, stdev
from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID

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
    
    # =========================================================================
    # CYCLE EVENT MANAGEMENT
    # =========================================================================
    
    def create_cycle_event(
        self,
        partner_id: str,
        event_type: str,
        event_date: date,
        notes: Optional[str] = None,
        cycle_day: Optional[int] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Optional[str]:
        """
        Create a cycle event and update predictions if it's a period_start.
        
        Args:
            partner_id: "partner_a" or "partner_b"
            event_type: "period_start", "period_end", "ovulation", etc.
            event_date: The date of the event
            notes: Optional notes
            cycle_day: Day of cycle (auto-calculated if period_start)
            relationship_id: Relationship ID
        
        Returns:
            Event ID if created successfully
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # If this is a period_start, calculate cycle length from previous period
            cycle_length = None
            if event_type == "period_start":
                cycle_day = 1  # First day of period is always day 1
                
                # Find previous period_start to calculate cycle length
                cursor.execute("""
                    SELECT event_date FROM cycle_events
                    WHERE partner_id = %s AND event_type = 'period_start' AND event_date < %s
                    ORDER BY event_date DESC LIMIT 1;
                """, (partner_id, event_date))
                
                prev_period = cursor.fetchone()
                if prev_period:
                    prev_date = prev_period[0]
                    cycle_length = (event_date - prev_date).days
                    logger.info(f"📅 Calculated cycle length: {cycle_length} days (from {prev_date} to {event_date})")
            
            # Insert the event
            cursor.execute("""
                INSERT INTO cycle_events 
                (relationship_id, partner_id, event_type, event_date, timestamp, notes, cycle_day, cycle_length)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (relationship_id, partner_id, event_type, event_date, datetime.now(), notes, cycle_day, cycle_length))
            
            event_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            # If period_start, update predictions
            if event_type == "period_start":
                self.update_cycle_predictions(partner_id, relationship_id)
            
            logger.info(f"✅ Created cycle event: {event_type} on {event_date} for {partner_id}")
            return str(event_id)
            
        except Exception as e:
            logger.error(f"❌ Error creating cycle event: {e}")
            if self.db.conn:
                self.db.conn.rollback()
            return None
    
    def get_cycle_events(
        self,
        partner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get cycle events for a partner within a date range."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Default to last 90 days if no dates specified
            if not start_date:
                start_date = date.today() - timedelta(days=90)
            if not end_date:
                end_date = date.today() + timedelta(days=30)
            
            cursor.execute("""
                SELECT id, event_type, event_date, notes, cycle_day, cycle_length, timestamp
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
                    "cycle_length": row[5],
                    "color": EVENT_COLORS.get(row[1], "#ec4899"),
                    "logged_at": row[6].isoformat() if row[6] else None
                })
            
            cursor.close()
            return events
            
        except Exception as e:
            logger.error(f"❌ Error getting cycle events: {e}")
            return []
    
    def _get_cycle_event_title(self, event_type: str) -> str:
        """Get human-readable title for cycle event type."""
        titles = {
            "period_start": "🩸 Period Started",
            "period_end": "Period Ended",
            "ovulation": "🥚 Ovulation",
            "fertile_start": "💕 Fertile Window Start",
            "fertile_end": "Fertile Window End",
            "pms_start": "⚠️ PMS Phase",
        }
        return titles.get(event_type, event_type.replace("_", " ").title())
    
    # =========================================================================
    # CYCLE PREDICTIONS
    # =========================================================================
    
    def update_cycle_predictions(
        self,
        partner_id: str,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> bool:
        """
        Update cycle predictions based on historical data.
        Uses average cycle length from past cycles.
        
        Args:
            partner_id: Partner to update predictions for
            relationship_id: Relationship ID
        
        Returns:
            True if predictions updated successfully
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get all period_start events to calculate average cycle length
            cursor.execute("""
                SELECT event_date, cycle_length FROM cycle_events
                WHERE partner_id = %s AND event_type = 'period_start'
                ORDER BY event_date DESC
                LIMIT 12;  -- Use last 12 cycles max
            """, (partner_id,))
            
            period_data = cursor.fetchall()
            
            if not period_data:
                logger.warning(f"⚠️ No period data for {partner_id}, cannot predict")
                cursor.close()
                return False
            
            # Calculate average cycle length
            cycle_lengths = [row[1] for row in period_data if row[1] is not None]
            
            if len(cycle_lengths) >= 2:
                avg_cycle_length = round(mean(cycle_lengths))
                confidence = min(0.95, 0.50 + (len(cycle_lengths) * 0.05))  # More data = higher confidence
                
                # Calculate standard deviation for confidence adjustment
                if len(cycle_lengths) >= 3:
                    std_dev = stdev(cycle_lengths)
                    # High variance = lower confidence
                    if std_dev > 5:
                        confidence *= 0.7
                    elif std_dev > 3:
                        confidence *= 0.85
            else:
                avg_cycle_length = DEFAULT_CYCLE_LENGTH
                confidence = 0.50
            
            logger.info(f"📊 Cycle stats for {partner_id}: avg={avg_cycle_length} days, confidence={confidence:.2f}, based on {len(cycle_lengths)} cycles")
            
            # Get most recent period start
            last_period_date = period_data[0][0]
            
            # Clear old predictions
            cursor.execute("""
                DELETE FROM cycle_predictions
                WHERE partner_id = %s AND relationship_id = %s;
            """, (partner_id, relationship_id))
            
            # Generate predictions for next 3 cycles
            predictions = []
            current_cycle_start = last_period_date
            
            for cycle_num in range(3):
                # Next period start
                next_period_start = current_cycle_start + timedelta(days=avg_cycle_length)
                predictions.append(("period_start", next_period_start, confidence))
                
                # Period end (assume 5 days)
                period_end = next_period_start + timedelta(days=DEFAULT_PERIOD_LENGTH)
                predictions.append(("period_end", period_end, confidence * 0.9))
                
                # Ovulation (typically day 14)
                ovulation_date = next_period_start + timedelta(days=DEFAULT_OVULATION_DAY - 1)
                predictions.append(("ovulation", ovulation_date, confidence * 0.8))
                
                # Fertile window (days 10-16)
                fertile_start = next_period_start + timedelta(days=DEFAULT_FERTILE_WINDOW_START - 1)
                fertile_end = next_period_start + timedelta(days=DEFAULT_FERTILE_WINDOW_END - 1)
                predictions.append(("fertile_start", fertile_start, confidence * 0.75))
                predictions.append(("fertile_end", fertile_end, confidence * 0.75))
                
                # PMS phase (days 21-28)
                pms_start = next_period_start + timedelta(days=DEFAULT_PMS_START_DAY - 1)
                predictions.append(("pms_start", pms_start, confidence * 0.7))
                
                current_cycle_start = next_period_start
            
            # Insert predictions
            for pred_type, pred_date, pred_confidence in predictions:
                cursor.execute("""
                    INSERT INTO cycle_predictions 
                    (relationship_id, partner_id, prediction_type, predicted_date, confidence, based_on_cycles)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (relationship_id, partner_id, pred_type, pred_date, pred_confidence, len(cycle_lengths)))
            
            conn.commit()
            cursor.close()
            
            logger.info(f"✅ Updated {len(predictions)} cycle predictions for {partner_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating cycle predictions: {e}")
            if self.db.conn:
                self.db.conn.rollback()
            return False
    
    def get_cycle_predictions(
        self,
        partner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get cycle predictions for a partner within a date range."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if not start_date:
                start_date = date.today()
            if not end_date:
                end_date = date.today() + timedelta(days=90)
            
            cursor.execute("""
                SELECT id, prediction_type, predicted_date, confidence, based_on_cycles
                FROM cycle_predictions
                WHERE partner_id = %s AND relationship_id = %s
                AND predicted_date BETWEEN %s AND %s
                ORDER BY predicted_date ASC;
            """, (partner_id, relationship_id, start_date, end_date))
            
            predictions = []
            for row in cursor.fetchall():
                predictions.append({
                    "id": str(row[0]),
                    "type": "prediction",
                    "prediction_type": row[1],
                    "predicted_date": row[2].isoformat() if row[2] else None,
                    "title": f"📌 Predicted: {self._get_cycle_event_title(row[1])}",
                    "confidence": float(row[3]) if row[3] else 0.5,
                    "based_on_cycles": row[4],
                    "color": EVENT_COLORS.get(row[1], "#ec4899"),
                    "is_prediction": True
                })
            
            cursor.close()
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Error getting cycle predictions: {e}")
            return []
    
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get most recent period start
            cursor.execute("""
                SELECT event_date, cycle_length FROM cycle_events
                WHERE partner_id = %s AND event_type = 'period_start' AND event_date <= %s
                ORDER BY event_date DESC LIMIT 1;
            """, (partner_id, target_date))
            
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return {
                    "phase_name": "Unknown",
                    "day_of_cycle": None,
                    "days_until_period": None,
                    "risk_level": "unknown",
                    "description": "Not enough cycle data to determine phase",
                    "confidence": 0.0
                }
            
            last_period_date, cycle_length = result
            cycle_length = cycle_length or DEFAULT_CYCLE_LENGTH
            
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
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
            
            cursor.close()
            
            # Sort by date
            events.sort(key=lambda x: x["event_date"])
            return events
            
        except Exception as e:
            logger.error(f"❌ Error getting memorable dates: {e}")
            return []
    
    def get_upcoming_events(
        self,
        days_ahead: int = 14,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> List[Dict[str, Any]]:
        """Get upcoming events (anniversaries, birthdays, predicted cycle events)."""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        events = []
        
        # Get memorable dates
        memorable = self.get_memorable_dates(today, end_date, relationship_id=relationship_id)
        events.extend(memorable)
        
        # Get cycle predictions (for partner_b / Elara)
        predictions = self.get_cycle_predictions("partner_b", today, end_date, relationship_id)
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
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
            cursor.close()
            
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
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
            
            cursor.close()
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            if not start_date:
                start_date = date.today() - timedelta(days=90)
            if not end_date:
                end_date = date.today() + timedelta(days=1)
            
            cursor.execute("""
                SELECT id, started_at, ended_at, status, metadata
                FROM conflicts
                WHERE relationship_id = %s
                AND started_at BETWEEN %s AND %s
                ORDER BY started_at ASC;
            """, (relationship_id, datetime.combine(start_date, datetime.min.time()),
                  datetime.combine(end_date, datetime.max.time())))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    "id": str(row[0]),
                    "type": "conflict",
                    "event_type": "conflict",
                    "event_date": row[1].date().isoformat() if row[1] else None,
                    "title": "⚠️ Conflict",
                    "started_at": row[1].isoformat() if row[1] else None,
                    "ended_at": row[2].isoformat() if row[2] else None,
                    "status": row[3],
                    "color": EVENT_COLORS["conflict"],
                    "metadata": row[4] if row[4] else {}
                })
            
            cursor.close()
            return events
            
        except Exception as e:
            logger.error(f"❌ Error getting conflict events: {e}")
            return []
    
    # =========================================================================
    # AGGREGATED CALENDAR VIEW
    # =========================================================================
    
    def get_calendar_events(
        self,
        year: int,
        month: int,
        include_predictions: bool = True,
        filters: List[str] = None,
        relationship_id: str = DEFAULT_RELATIONSHIP_ID
    ) -> Dict[str, Any]:
        """
        Get all calendar events for a month (chronologically ordered).
        
        Args:
            year: Year
            month: Month (1-12)
            include_predictions: Whether to include cycle predictions
            filters: List of event types to include (None = all)
            relationship_id: Relationship ID
        
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
            cycle_events = self.get_cycle_events("partner_b", start_date, end_date, relationship_id)
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
            predictions = self.get_cycle_predictions("partner_b", start_date, end_date, relationship_id)
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
        
        # Calculate summary stats
        stats = {
            "total_events": len(all_events),
            "cycle_events": len([e for e in all_events if e.get("type") == "cycle"]),
            "intimacy_events": len([e for e in all_events if e.get("type") == "intimacy"]),
            "conflict_events": len([e for e in all_events if e.get("type") == "conflict"]),
            "memorable_events": len([e for e in all_events if e.get("type") == "memorable"]),
            "predictions": len([e for e in all_events if e.get("type") == "prediction"]),
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
        lookback_days: int = 180
    ) -> Dict[str, Any]:
        """
        Analyze correlation between conflicts and cycle phases.
        
        Returns:
            Dict with correlation stats and insights
        """
        try:
            # Get conflicts from last N days
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
        
        Returns:
            Formatted string with cycle phase, upcoming events, and patterns
        """
        insights = []
        
        # Current cycle phase
        phase = self.get_current_cycle_phase("partner_b", relationship_id=relationship_id)
        if phase.get("phase_name") != "Unknown":
            phase_emoji = phase.get("emoji", "📅")
            insights.append(f"📅 CURRENT CYCLE PHASE (Elara)")
            insights.append(f"   {phase_emoji} Phase: {phase.get('phase_name')}")
            insights.append(f"   Day of cycle: {phase.get('day_of_cycle', 'N/A')}")
            insights.append(f"   Days until period: {phase.get('days_until_period', 'N/A')}")
            insights.append(f"   Risk level: {phase.get('risk_level', 'unknown').upper()}")
            insights.append(f"   Note: {phase.get('description', '')}")
            insights.append("")
        
        # Upcoming events (next 14 days)
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
        
        # Conflict-cycle correlation
        correlation = self.get_conflict_cycle_correlation(relationship_id)
        if correlation.get("has_data"):
            insights.append("📊 CONFLICT PATTERN INSIGHT")
            insights.append(f"   {correlation.get('insight', 'No patterns detected')}")
            insights.append("")
        
        # Risk assessment for today
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


# Global instance
try:
    calendar_service = CalendarService()
except Exception as e:
    logger.error(f"❌ Failed to initialize CalendarService: {e}")
    calendar_service = None

