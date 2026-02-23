"""
Celery tasks for weekly relationship digest generation.
Scheduled via Celery Beat (Monday 9 AM UTC).
"""
import logging
import asyncio

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.digest_tasks.generate_all_digests")
def generate_all_digests():
    """Generate weekly digests for all active relationships."""
    from app.services.db_service import db_service

    relationships = db_service.get_all_active_relationships()
    logger.info(f"Generating digests for {len(relationships)} active relationships")

    results = []
    for rel in relationships:
        try:
            result = generate_digest_for_relationship.delay(rel["relationship_id"])
            results.append({"relationship_id": rel["relationship_id"], "task_id": result.id})
        except Exception as e:
            logger.error(f"Failed to dispatch digest for {rel['relationship_id']}: {e}")

    return {"dispatched": len(results), "results": results}


@celery_app.task(name="app.tasks.digest_tasks.generate_digest_for_relationship")
def generate_digest_for_relationship(relationship_id: str):
    """Generate a weekly digest for a single relationship."""
    from app.services.digest_service import digest_service

    logger.info(f"Generating digest for relationship {relationship_id}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            digest_service.generate_weekly_digest(relationship_id)
        )
        logger.info(f"Digest generated for {relationship_id}: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to generate digest for {relationship_id}: {e}")
        raise
    finally:
        loop.close()
