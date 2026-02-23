"""
Conflict Prevention Alert Service

Detects patterns that may indicate rising tension and generates
personalized alerts to help couples proactively avoid escalation.

Alert types:
- tension_rising: Messaging sentiment drops below threshold
- recurring_trigger: Same trigger phrase detected 3+ times
- cool_down_reminder: Post-conflict timer reminder
- check_in_prompt: Periodic check-in when no positive interaction
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertMessage(BaseModel):
    """LLM-generated alert message."""
    title: str = Field(..., description="Short alert title (under 60 chars)")
    message: str = Field(..., description="Supportive, actionable message (1-2 sentences)")


class AlertService:
    """Detection and generation of prevention alerts."""

    async def check_for_alerts(
        self,
        relationship_id: str,
        trigger_context: Dict[str, Any] = None,
    ) -> List[Dict]:
        """
        Main detection method. Called after message analysis or post-fight analysis.
        Returns list of newly created alerts.
        """
        from app.services.db_service import db_service

        created_alerts = []
        trigger_context = trigger_context or {}
        trigger_type = trigger_context.get("type", "")

        try:
            # Check for tension_rising (sentiment drop in messaging)
            if trigger_type == "message_analysis":
                alert = await self._check_tension_rising(
                    relationship_id, trigger_context
                )
                if alert:
                    created_alerts.append(alert)

            # Check for recurring_trigger (after post-fight analysis)
            if trigger_type == "post_fight_analysis":
                alert = await self._check_recurring_triggers(
                    relationship_id, trigger_context
                )
                if alert:
                    created_alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")

        return created_alerts

    async def _check_tension_rising(
        self, relationship_id: str, context: Dict
    ) -> Optional[Dict]:
        """Detect when messaging sentiment is dropping."""
        from app.services.db_service import db_service

        sentiment_score = context.get("sentiment_score")
        if sentiment_score is None:
            return None

        # Threshold: alert if sentiment drops below 0.3
        if sentiment_score >= 0.3:
            return None

        # Don't spam: check if a tension_rising alert was already created recently
        recent_alerts = db_service.get_active_alerts(relationship_id)
        recent_tension = [
            a for a in recent_alerts
            if a.get("alert_type") == "tension_rising"
            and a.get("created_at")
            and (datetime.now() - a["created_at"]).total_seconds() < 7200  # 2 hours
        ]
        if recent_tension:
            return None

        alert_msg = await self._generate_alert_message(
            alert_type="tension_rising",
            relationship_id=relationship_id,
            context=context,
        )

        alert_id = db_service.create_alert(
            relationship_id=relationship_id,
            alert_type="tension_rising",
            severity="medium",
            title=alert_msg.title if alert_msg else "Tension may be rising",
            message=alert_msg.message if alert_msg else "Your recent messages suggest some tension. Consider taking a moment to check in with each other.",
            context=context,
        )

        return {"id": alert_id, "type": "tension_rising", "severity": "medium"}

    async def _check_recurring_triggers(
        self, relationship_id: str, context: Dict
    ) -> Optional[Dict]:
        """Detect when the same trigger phrase appears 3+ times."""
        from app.services.db_service import db_service
        from psycopg2.extras import RealDictCursor

        try:
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT phrase, COUNT(*) as count
                        FROM trigger_phrases
                        WHERE relationship_id = %s
                          AND created_at >= NOW() - INTERVAL '30 days'
                        GROUP BY phrase
                        HAVING COUNT(*) >= 3
                        ORDER BY count DESC
                        LIMIT 1;
                    """, (relationship_id,))
                    row = cursor.fetchone()

            if not row:
                return None

            phrase = row["phrase"]
            count = row["count"]

            # Don't duplicate
            recent_alerts = db_service.get_active_alerts(relationship_id)
            if any(
                a.get("alert_type") == "recurring_trigger"
                and a.get("context", {}).get("phrase") == phrase
                for a in recent_alerts
            ):
                return None

            alert_msg = await self._generate_alert_message(
                alert_type="recurring_trigger",
                relationship_id=relationship_id,
                context={"phrase": phrase, "count": count},
            )

            alert_id = db_service.create_alert(
                relationship_id=relationship_id,
                alert_type="recurring_trigger",
                severity="high" if count >= 5 else "medium",
                title=alert_msg.title if alert_msg else f"Recurring trigger detected",
                message=alert_msg.message if alert_msg else f'The phrase "{phrase}" has come up {count} times recently. This may be a deeper issue worth discussing calmly.',
                context={"phrase": phrase, "count": count},
            )

            return {"id": alert_id, "type": "recurring_trigger", "severity": "medium"}

        except Exception as e:
            logger.error(f"Error checking recurring triggers: {e}")
            return None

    async def create_cool_down_reminder(
        self, relationship_id: str, conflict_id: str
    ) -> Optional[Dict]:
        """Create a cool-down reminder 2 hours after a conflict ends."""
        from app.services.db_service import db_service

        alert_id = db_service.create_alert(
            relationship_id=relationship_id,
            alert_type="cool_down_reminder",
            severity="low",
            title="Time for a check-in",
            message="It's been a couple of hours since your last disagreement. When you're both ready, a gentle check-in can help reconnect.",
            context={"conflict_id": conflict_id},
        )

        return {"id": alert_id, "type": "cool_down_reminder"}

    async def create_checkin_prompt(self, relationship_id: str) -> Optional[Dict]:
        """Create a check-in prompt when no positive interaction for several days."""
        from app.services.db_service import db_service

        alert_id = db_service.create_alert(
            relationship_id=relationship_id,
            alert_type="check_in_prompt",
            severity="low",
            title="Time to reconnect",
            message="It's been a few days since your last positive interaction. A small gesture of appreciation can make a big difference.",
            context={},
        )

        return {"id": alert_id, "type": "check_in_prompt"}

    async def _generate_alert_message(
        self,
        alert_type: str,
        relationship_id: str,
        context: Dict,
    ) -> Optional[AlertMessage]:
        """Use LLM to generate a personalized alert message."""
        try:
            from app.services.llm_service import llm_service
            from app.services.db_service import db_service

            names = db_service.get_partner_names(relationship_id)
            partner_a = names.get("partner_a", "Partner A")
            partner_b = names.get("partner_b", "Partner B")

            type_descriptions = {
                "tension_rising": f"Messaging between {partner_a} and {partner_b} shows declining sentiment. Context: {context}",
                "recurring_trigger": f'The phrase "{context.get("phrase", "")}" has appeared {context.get("count", 0)} times in recent conflicts between {partner_a} and {partner_b}.',
                "cool_down_reminder": f"A conflict just ended between {partner_a} and {partner_b}. Time for a gentle reminder.",
                "check_in_prompt": f"No positive interactions detected recently between {partner_a} and {partner_b}.",
            }

            prompt = f"""Generate a brief, warm, supportive relationship alert.
Alert type: {alert_type}
Situation: {type_descriptions.get(alert_type, "")}

Be empathetic, non-judgmental, and actionable. Keep it concise."""

            result = llm_service.structured_output(
                messages=[
                    {"role": "system", "content": "You are Luna, a compassionate AI relationship advisor."},
                    {"role": "user", "content": prompt},
                ],
                response_model=AlertMessage,
                temperature=0.7,
            )
            return result

        except Exception as e:
            logger.warning(f"LLM alert generation failed: {e}")
            return None


alert_service = AlertService()
