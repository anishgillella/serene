"""
Celery tasks for scheduled alert checks.

- check_cool_down_reminders: Every 30 min, checks for post-fight cooldown timers
- check_periodic_checkins: Daily, checks for extended no-positive-interaction periods
"""
import logging
import asyncio
from datetime import datetime, timedelta

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.alert_tasks.check_cool_down_reminders")
def check_cool_down_reminders():
    """Check for conflicts that ended ~2 hours ago and create cool-down reminders."""
    from app.services.db_service import db_service
    from app.services.alert_service import alert_service
    from psycopg2.extras import RealDictCursor

    try:
        # Find conflicts that ended 1.5-2.5 hours ago (window to avoid duplicates)
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT c.id, c.relationship_id
                    FROM conflicts c
                    WHERE c.ended_at IS NOT NULL
                      AND c.ended_at BETWEEN NOW() - INTERVAL '2.5 hours' AND NOW() - INTERVAL '1.5 hours'
                      AND NOT EXISTS (
                          SELECT 1 FROM prevention_alerts pa
                          WHERE pa.relationship_id = c.relationship_id
                            AND pa.alert_type = 'cool_down_reminder'
                            AND pa.context->>'conflict_id' = c.id::text
                      );
                """)
                conflicts = cursor.fetchall()

        if not conflicts:
            return {"checked": 0, "created": 0}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        created = 0
        try:
            for c in conflicts:
                result = loop.run_until_complete(
                    alert_service.create_cool_down_reminder(
                        str(c["relationship_id"]), str(c["id"])
                    )
                )
                if result:
                    created += 1
        finally:
            loop.close()

        logger.info(f"Cool-down check: {len(conflicts)} eligible, {created} alerts created")
        return {"checked": len(conflicts), "created": created}

    except Exception as e:
        logger.error(f"Error in cool-down check: {e}")
        return {"error": str(e)}


@celery_app.task(name="app.tasks.alert_tasks.check_periodic_checkins")
def check_periodic_checkins():
    """Check for relationships with no positive interaction in 3+ days."""
    from app.services.db_service import db_service
    from app.services.alert_service import alert_service
    from psycopg2.extras import RealDictCursor

    try:
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Find relationships with no positive check-in in 3+ days
                # and no existing active check_in_prompt
                cursor.execute("""
                    SELECT r.id as relationship_id
                    FROM relationships r
                    WHERE EXISTS (
                        SELECT 1 FROM conflicts c WHERE c.relationship_id = r.id
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM daily_checkins dc
                        WHERE dc.relationship_id = r.id
                          AND dc.day_rating = 'positive'
                          AND dc.checkin_date >= CURRENT_DATE - 3
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM prevention_alerts pa
                        WHERE pa.relationship_id = r.id
                          AND pa.alert_type = 'check_in_prompt'
                          AND pa.is_dismissed = FALSE
                          AND pa.created_at >= NOW() - INTERVAL '3 days'
                    );
                """)
                relationships = cursor.fetchall()

        if not relationships:
            return {"checked": 0, "created": 0}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        created = 0
        try:
            for r in relationships:
                result = loop.run_until_complete(
                    alert_service.create_checkin_prompt(str(r["relationship_id"]))
                )
                if result:
                    created += 1
        finally:
            loop.close()

        logger.info(f"Check-in check: {len(relationships)} eligible, {created} alerts created")
        return {"checked": len(relationships), "created": created}

    except Exception as e:
        logger.error(f"Error in periodic check-in: {e}")
        return {"error": str(e)}
