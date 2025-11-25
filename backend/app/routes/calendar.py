"""
Calendar API routes for managing relationship events, cycle tracking, and insights.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.services.calendar_service import calendar_service
from app.services.db_service import DEFAULT_RELATIONSHIP_ID
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# =========================================================================
# PYDANTIC MODELS
# =========================================================================

class CycleEventCreate(BaseModel):
    """Request model for creating a cycle event."""
    partner_id: str = Field(default="partner_b", description="Partner ID (partner_a or partner_b)")
    event_type: str = Field(..., description="Event type: period_start, period_end, ovulation, etc.")
    event_date: date = Field(..., description="Date of the event")
    notes: Optional[str] = Field(None, description="Optional notes")


class MemorableDateCreate(BaseModel):
    """Request model for creating a memorable date."""
    title: str = Field(..., description="Event title (e.g., 'First Anniversary')")
    event_date: date = Field(..., description="Date of the event")
    event_type: str = Field(default="custom", description="Event type: anniversary, birthday, first_date, milestone, custom")
    description: Optional[str] = Field(None, description="Optional description")
    is_recurring: bool = Field(default=True, description="Whether event recurs annually")
    reminder_days: int = Field(default=7, description="Days before to remind")
    color_tag: Optional[str] = Field(None, description="UI color (hex)")
    partner_id: Optional[str] = Field(None, description="Related partner (for birthdays)")


class IntimacyEventCreate(BaseModel):
    """Request model for creating an intimacy event."""
    event_date: Optional[date] = Field(None, description="Date of event (defaults to today)")
    initiator_partner_id: Optional[str] = Field(None, description="Who initiated")
    notes: Optional[str] = Field(None, description="Optional notes")


class CalendarEventsResponse(BaseModel):
    """Response model for calendar events."""
    year: int
    month: int
    events: List[dict]
    events_by_date: dict
    stats: dict


class CyclePhaseResponse(BaseModel):
    """Response model for current cycle phase."""
    phase_name: str
    day_of_cycle: Optional[int]
    days_until_period: Optional[int]
    risk_level: str
    description: str
    confidence: float
    emoji: Optional[str] = None


class InsightsResponse(BaseModel):
    """Response model for calendar insights."""
    cycle_phase: dict
    upcoming_events: List[dict]
    conflict_correlation: dict
    llm_context: str


# =========================================================================
# CYCLE EVENTS ENDPOINTS
# =========================================================================

@router.post("/cycle-events", summary="Create a cycle event")
async def create_cycle_event(event: CycleEventCreate):
    """
    Create a new cycle event (period start, ovulation, etc.).
    
    If event_type is 'period_start', cycle predictions will be automatically updated.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    event_id = calendar_service.create_cycle_event(
        partner_id=event.partner_id,
        event_type=event.event_type,
        event_date=event.event_date,
        notes=event.notes
    )
    
    if not event_id:
        raise HTTPException(status_code=500, detail="Failed to create cycle event")
    
    return {
        "success": True,
        "event_id": event_id,
        "message": f"Created {event.event_type} event for {event.event_date}"
    }


@router.get("/cycle-events", summary="Get cycle events")
async def get_cycle_events(
    partner_id: str = Query(default="partner_b", description="Partner ID"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
):
    """Get cycle events for a partner within a date range."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    events = calendar_service.get_cycle_events(
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {"events": events, "count": len(events)}


@router.get("/cycle-phase", summary="Get current cycle phase")
async def get_cycle_phase(
    partner_id: str = Query(default="partner_b", description="Partner ID"),
    target_date: Optional[date] = Query(None, description="Date to check (defaults to today)")
):
    """
    Get the current cycle phase for a partner.
    
    Returns phase name, day of cycle, risk level, and recommendations.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    phase = calendar_service.get_current_cycle_phase(
        partner_id=partner_id,
        target_date=target_date
    )
    
    return phase


@router.get("/cycle-predictions", summary="Get cycle predictions")
async def get_cycle_predictions(
    partner_id: str = Query(default="partner_b", description="Partner ID"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
):
    """Get predicted cycle events based on historical data."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    predictions = calendar_service.get_cycle_predictions(
        partner_id=partner_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {"predictions": predictions, "count": len(predictions)}


@router.post("/cycle-predictions/update", summary="Update cycle predictions")
async def update_cycle_predictions(
    partner_id: str = Query(default="partner_b", description="Partner ID")
):
    """Force update cycle predictions based on latest data."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    success = calendar_service.update_cycle_predictions(partner_id=partner_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update predictions - not enough cycle data")
    
    return {"success": True, "message": "Cycle predictions updated"}


# =========================================================================
# MEMORABLE DATES ENDPOINTS
# =========================================================================

@router.post("/memorable-dates", summary="Create a memorable date")
async def create_memorable_date(event: MemorableDateCreate):
    """
    Create a new memorable date (anniversary, birthday, milestone).
    
    Recurring events will appear on the calendar every year.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    event_id = calendar_service.create_memorable_date(
        title=event.title,
        event_date=event.event_date,
        event_type=event.event_type,
        description=event.description,
        is_recurring=event.is_recurring,
        reminder_days=event.reminder_days,
        color_tag=event.color_tag,
        partner_id=event.partner_id
    )
    
    if not event_id:
        raise HTTPException(status_code=500, detail="Failed to create memorable date")
    
    return {
        "success": True,
        "event_id": event_id,
        "message": f"Created '{event.title}' for {event.event_date}"
    }


@router.get("/memorable-dates", summary="Get memorable dates")
async def get_memorable_dates(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    include_recurring: bool = Query(True, description="Include recurring events")
):
    """Get memorable dates within a date range."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    events = calendar_service.get_memorable_dates(
        start_date=start_date,
        end_date=end_date,
        include_recurring=include_recurring
    )
    
    return {"events": events, "count": len(events)}


# =========================================================================
# INTIMACY EVENTS ENDPOINTS
# =========================================================================

@router.post("/intimacy-events", summary="Create an intimacy event")
async def create_intimacy_event(event: IntimacyEventCreate):
    """Create a new intimacy event."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    event_id = calendar_service.create_intimacy_event(
        initiator_partner_id=event.initiator_partner_id,
        event_date=event.event_date,
        notes=event.notes
    )
    
    if not event_id:
        raise HTTPException(status_code=500, detail="Failed to create intimacy event")
    
    return {
        "success": True,
        "event_id": event_id,
        "message": f"Created intimacy event"
    }


@router.get("/intimacy-events", summary="Get intimacy events")
async def get_intimacy_events(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
):
    """Get intimacy events within a date range."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    events = calendar_service.get_intimacy_events(
        start_date=start_date,
        end_date=end_date
    )
    
    return {"events": events, "count": len(events)}


# =========================================================================
# AGGREGATED CALENDAR ENDPOINTS
# =========================================================================

@router.get("/events", summary="Get all calendar events for a month")
async def get_calendar_events(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    include_predictions: bool = Query(True, description="Include cycle predictions"),
    filters: Optional[str] = Query(None, description="Comma-separated filters: cycle,intimacy,conflict,memorable,prediction")
):
    """
    Get all calendar events for a month (chronologically ordered).
    
    Returns events grouped by date with summary statistics.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    # Parse filters
    filter_list = None
    if filters:
        filter_list = [f.strip() for f in filters.split(",")]
    
    result = calendar_service.get_calendar_events(
        year=year,
        month=month,
        include_predictions=include_predictions,
        filters=filter_list
    )
    
    return result


@router.get("/upcoming", summary="Get upcoming events")
async def get_upcoming_events(
    days_ahead: int = Query(14, ge=1, le=90, description="Days to look ahead")
):
    """Get upcoming events (anniversaries, birthdays, predicted cycle events)."""
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    events = calendar_service.get_upcoming_events(days_ahead=days_ahead)
    
    return {"events": events, "count": len(events), "days_ahead": days_ahead}


# =========================================================================
# INSIGHTS ENDPOINTS
# =========================================================================

@router.get("/insights", summary="Get calendar insights")
async def get_calendar_insights():
    """
    Get comprehensive calendar insights including:
    - Current cycle phase
    - Upcoming events
    - Conflict-cycle correlation
    - LLM-ready context string
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    # Get current cycle phase
    cycle_phase = calendar_service.get_current_cycle_phase("partner_b")
    
    # Get upcoming events
    upcoming_events = calendar_service.get_upcoming_events(14)
    
    # Get conflict-cycle correlation
    correlation = calendar_service.get_conflict_cycle_correlation()
    
    # Get LLM-ready context
    llm_context = calendar_service.get_calendar_insights_for_llm()
    
    return {
        "cycle_phase": cycle_phase,
        "upcoming_events": upcoming_events,
        "conflict_correlation": correlation,
        "llm_context": llm_context
    }


@router.get("/insights/llm-context", summary="Get LLM-ready calendar context")
async def get_llm_calendar_context():
    """
    Get a formatted string of calendar insights ready for LLM injection.
    
    Use this for injecting calendar context into voice agent or repair plan generation.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    context = calendar_service.get_calendar_insights_for_llm()
    
    return {"context": context}


@router.get("/conflict-correlation", summary="Get conflict-cycle correlation analysis")
async def get_conflict_correlation(
    lookback_days: int = Query(180, ge=30, le=365, description="Days to analyze")
):
    """
    Analyze correlation between conflicts and cycle phases.
    
    Returns percentage of conflicts that occurred during each cycle phase.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    correlation = calendar_service.get_conflict_cycle_correlation(
        lookback_days=lookback_days
    )
    
    return correlation


# =========================================================================
# SEED DATA ENDPOINT (for testing)
# =========================================================================

@router.post("/seed-sample-data", summary="Seed sample calendar data (for testing)")
async def seed_sample_data():
    """
    Seed sample calendar data for testing.
    Creates sample cycle events, memorable dates, and intimacy events.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    try:
        today = date.today()
        
        # Seed some past period starts (to establish cycle pattern)
        # Assuming ~28 day cycle
        period_dates = [
            today - timedelta(days=56),  # 2 cycles ago
            today - timedelta(days=28),  # 1 cycle ago
        ]
        
        for period_date in period_dates:
            calendar_service.create_cycle_event(
                partner_id="partner_b",
                event_type="period_start",
                event_date=period_date,
                notes="Sample period data"
            )
            # Also add period end (5 days later)
            calendar_service.create_cycle_event(
                partner_id="partner_b",
                event_type="period_end",
                event_date=period_date + timedelta(days=5),
                notes="Sample period data"
            )
        
        # Seed some memorable dates
        memorable_dates = [
            {
                "title": "First Anniversary",
                "event_date": date(2024, 6, 15),
                "event_type": "anniversary",
                "description": "The day Adrian and Elara started dating"
            },
            {
                "title": "Elara's Birthday",
                "event_date": date(1998, 3, 22),
                "event_type": "birthday",
                "partner_id": "partner_b"
            },
            {
                "title": "Adrian's Birthday",
                "event_date": date(1997, 8, 10),
                "event_type": "birthday",
                "partner_id": "partner_a"
            },
            {
                "title": "First Date",
                "event_date": date(2024, 5, 1),
                "event_type": "first_date",
                "description": "Coffee at the corner cafe"
            }
        ]
        
        for md in memorable_dates:
            calendar_service.create_memorable_date(**md)
        
        # Seed some intimacy events
        intimacy_dates = [
            today - timedelta(days=7),
            today - timedelta(days=14),
            today - timedelta(days=21),
        ]
        
        for int_date in intimacy_dates:
            calendar_service.create_intimacy_event(event_date=int_date)
        
        return {
            "success": True,
            "message": "Sample data seeded successfully",
            "seeded": {
                "cycle_events": len(period_dates) * 2,
                "memorable_dates": len(memorable_dates),
                "intimacy_events": len(intimacy_dates)
            }
        }
        
    except Exception as e:
        logger.error(f"Error seeding sample data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to seed data: {e}")

