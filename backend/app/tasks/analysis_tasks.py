"""
Celery tasks for post-fight analysis.

Wraps the existing generate_analysis_and_repair_plan_background() logic
so it runs in a Celery worker instead of asyncio background tasks.
"""
import logging
import asyncio
from datetime import datetime

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.analysis_tasks.run_post_fight_analysis")
def run_post_fight_analysis(
    self,
    conflict_id: str,
    transcript_text: str,
    relationship_id: str,
    partner_a_id: str = "partner_a",
    partner_b_id: str = "partner_b",
    speaker_labels: dict = None,
    duration: float = 0.0,
):
    """
    Main Celery task for post-fight analysis.
    Delegates to the existing async background function.
    """
    from app.services.db_service import db_service

    celery_task_id = self.request.id
    logger.info(f"Celery task {celery_task_id}: Starting analysis for conflict {conflict_id}")

    # Create/update task status in DB
    try:
        db_service.create_task_status(
            task_type="post_fight_analysis",
            reference_id=conflict_id,
            relationship_id=relationship_id,
            celery_task_id=celery_task_id,
            status="processing",
        )
    except Exception as e:
        logger.warning(f"Failed to create task_status row: {e}")

    try:
        # Import the async function and run it in a new event loop
        from app.routes.post_fight import generate_analysis_and_repair_plan_background

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                generate_analysis_and_repair_plan_background(
                    conflict_id=conflict_id,
                    transcript_text=transcript_text,
                    relationship_id=relationship_id,
                    partner_a_id=partner_a_id,
                    partner_b_id=partner_b_id,
                    speaker_labels=speaker_labels or {},
                    duration=duration,
                    timestamp=datetime.now(),
                )
            )
        finally:
            loop.close()

        # Mark completed
        try:
            db_service.update_task_status(
                celery_task_id=celery_task_id,
                status="completed",
                result={"message": "Analysis and repair plans generated successfully"},
            )
        except Exception as e:
            logger.warning(f"Failed to update task_status to completed: {e}")

        logger.info(f"Celery task {celery_task_id}: Completed for conflict {conflict_id}")
        return {"status": "completed", "conflict_id": conflict_id}

    except Exception as e:
        logger.error(f"Celery task {celery_task_id}: Failed for conflict {conflict_id}: {e}")

        try:
            db_service.update_task_status(
                celery_task_id=celery_task_id,
                status="failed",
                error_message=str(e),
            )
        except Exception:
            pass

        raise  # Let Celery handle retry/failure
