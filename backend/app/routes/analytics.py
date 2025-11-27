"""
Analytics API routes for relationship insights and dashboard data.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.calendar_service import calendar_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

from app.services.db_service import DEFAULT_RELATIONSHIP_ID

@router.get("/dashboard", summary="Get analytics dashboard data")
async def get_analytics_dashboard(
    relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID, description="Relationship ID"),
    partner_id: str = Query(default="partner_b", description="Partner ID")
):
    """
    Get aggregated data for the analytics dashboard.
    Includes health score, trends, cycle correlation, and tension forecast.
    """
    if not calendar_service:
        raise HTTPException(status_code=500, detail="Calendar service not available")
    
    try:
        data = calendar_service.get_analytics_dashboard_data(
            relationship_id=relationship_id,
            partner_id=partner_id
        )
        return data
    except Exception as e:
        logger.error(f"Error fetching analytics dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
