# Phase 3: Luna's Awareness - Context-Aware Mediation

**Goal**: Integrate conflict intelligence into Luna's real-time mediation capabilities

**Timeline**: 2-3 weeks

**Deliverables**:
- Luna context injection system
- Intelligent response generation
- Real-time pattern awareness
- Repair plan personalization

**Depends On**: Phase 1 (Data) + Phase 2 (Analytics)

---

## 3.1 Luna Context Injection

### Session Context Building

When Luna starts a mediation session, pre-load relevant context:

```python
async def build_mediation_context(
    relationship_id: UUID,
    current_conflict_id: Optional[UUID] = None
) -> MediationContext:
    """
    Build comprehensive context for Luna's awareness.
    Called when user starts mediator session.
    """

    context = MediationContext()

    # 1. Current Conflict Context
    if current_conflict_id:
        conflict = await db.get_conflict(current_conflict_id)
        context.current_conflict = {
            "topic": conflict.topic,
            "resentment_level": conflict.resentment_level,
            "parent_conflict": conflict.parent_conflict_id,
            "unmet_needs": conflict.unmet_needs
        }

    # 2. Unresolved Issues
    unresolved = await db.get_unresolved_conflicts(relationship_id)
    context.unresolved_issues = [
        {
            "conflict_id": c.id,
            "topic": c.topic,
            "days_unresolved": (now - c.created_at).days,
            "resentment_level": c.resentment_level,
            "unmet_needs": c.unmet_needs
        }
        for c in unresolved[:5]  # top 5 unresolved
    ]

    # 3. Chronic Unmet Needs
    chronic_needs = await pattern_service.track_chronic_needs(relationship_id)
    context.chronic_needs = [
        {
            "need": n.need,
            "conflict_count": n.conflict_count,
            "appears_in_percentage": f"{(n.conflict_count / total_conflicts) * 100:.1f}%"
        }
        for n in chronic_needs if n.is_chronic
    ]

    # 4. Recent Trigger Phrases
    trigger_analysis = await pattern_service.find_trigger_phrase_patterns(relationship_id)
    context.high_impact_triggers = trigger_analysis.most_impactful[:5]

    # 5. Escalation Risk
    risk = await pattern_service.calculate_escalation_risk(relationship_id)
    context.escalation_risk = {
        "score": risk.risk_score,
        "interpretation": risk.interpretation,
        "is_critical": risk.risk_score > 0.75
    }

    # 6. Conflict Chains
    chains = await pattern_service.identify_conflict_chains(relationship_id)
    context.active_chains = [c for c in chains if not c.is_resolved][:3]

    return context
```

### Context Prompt Template for Luna

```python
def build_luna_system_prompt(context: MediationContext) -> str:
    """
    Build system prompt that makes Luna aware of conflict patterns.
    Injected into every mediation turn.
    """

    prompt = f"""
You are Luna, a compassionate AI relationship mediator.

CURRENT SESSION CONTEXT:
"""

    if context.current_conflict:
        prompt += f"""
Current Conflict:
- Topic: {context.current_conflict['topic']}
- Resentment Level: {context.current_conflict['resentment_level']}/10
- Unmet Needs: {', '.join(context.current_conflict['unmet_needs'])}
"""

    if context.unresolved_issues:
        prompt += f"""
IMPORTANT - Unresolved Issues (likely contributing to tension):
"""
        for issue in context.unresolved_issues:
            days = issue['days_unresolved']
            prompt += f"- {issue['topic']} (unresolved for {days} days, resentment: {issue['resentment_level']}/10)\n"

    if context.chronic_needs:
        prompt += f"""
CHRONIC UNMET NEEDS (appear in {context.chronic_needs[0]['appears_in_percentage']} of conflicts):
These are the ROOT issues beneath surface complaints:
"""
        for need in context.chronic_needs:
            prompt += f"- {need['need'].replace('_', ' ')} (appears in {need['conflict_count']} conflicts)\n"

    if context.high_impact_triggers:
        prompt += f"""
ESCALATION TRIGGERS (phrases that intensify conflicts):
If you hear these, be extra attentive to underlying pain:
"""
        for trigger in context.high_impact_triggers:
            prompt += f"- \"{trigger['phrase']}\" (escalates {trigger['escalation_rate']*100:.0f}% of the time)\n"

    if context.escalation_risk['is_critical']:
        prompt += f"""
⚠️  CRITICAL: Relationship is at high escalation risk ({context.escalation_risk['score']:.1%})
- Multiple unresolved issues
- Recent rapid conflict recurrence
- Consider prioritizing root cause resolution over surface topic
"""

    prompt += """
YOUR ROLE:
1. Acknowledge the real issue, not just the surface complaint
2. Reference past unresolved issues if relevant
3. Identify which chronic unmet need is driving THIS conflict
4. Help them resolve the ROOT issue, not just the current fight
5. Validate that their resentment is understandable given history

REMEMBER: Surface conflicts are symptoms of deeper unmet needs.
"""

    return prompt
```

---

## 3.2 Intelligent Response Generation

### Luna's Enhanced Responses

```python
async def generate_luna_response(
    user_message: str,
    context: MediationContext,
    conversation_history: List[Turn]
) -> LunaResponse:
    """
    Generate Luna's response with awareness of conflict patterns.
    """

    # Check if user triggered an escalation pattern
    detected_triggers = detect_trigger_patterns(user_message, context)

    # Check if this connects to unresolved issues
    relevant_issues = identify_relevant_unresolved(user_message, context)

    # Build contextual prompt
    system_prompt = build_luna_system_prompt(context)

    if relevant_issues:
        system_prompt += f"""
The user just said something that connects to an unresolved issue:
{relevant_issues[0]['topic']} (from {relevant_issues[0]['days_unresolved']} days ago)

Gently surface this connection and help them see the pattern.
"""

    if detected_triggers:
        system_prompt += f"""
The user used a trigger phrase: "{detected_triggers[0]['phrase']}"
This phrase has escalated conflicts {detected_triggers[0]['escalation_rate']*100:.0f}% of the time.

Acknowledge their underlying pain rather than reacting to the phrase.
"""

    # Generate response
    response = await llm_service.generate_mediation_response(
        system_prompt=system_prompt,
        user_message=user_message,
        conversation_history=conversation_history
    )

    return LunaResponse(
        text=response,
        detected_patterns=[
            {"type": "trigger", "value": t['phrase']} for t in detected_triggers
        ] + [
            {"type": "unresolved_issue", "value": issue['topic']} for issue in relevant_issues
        ]
    )
```

### Example: What Luna Might Say

**Before (without context):**
```
I understand. The door is important to you.
Let's talk about how you can remember to close it.
```

**After (with context awareness):**
```
I'm hearing frustration about the door, but I'm noticing something else here.

You mentioned yesterday you both felt unheard about the dishes. Now today it's the door.
These aren't really about the door or dishes—they're about feeling appreciated and heard.

Can we step back? What do you both actually need from each other here?
When she says "You didn't do that yesterday," she's really saying "I don't feel like you're listening to me."

How can you both feel more heard?
```

---

## 3.3 Real-Time Pattern Detection

### During-Session Pattern Detection

```python
async def detect_escalation_in_realtime(
    conversation: List[Turn],
    context: MediationContext
) -> EscalationAlert:
    """
    Monitor conversation for signs of escalation.
    Alert Luna if pattern emerging.
    """

    recent_turns = conversation[-5:]  # last 5 exchanges
    trigger_phrase_count = 0
    emotional_escalation = False

    for turn in recent_turns:
        # Count trigger phrases
        for trigger in context.high_impact_triggers:
            if trigger['phrase'].lower() in turn.text.lower():
                trigger_phrase_count += 1

        # Detect emotional escalation (multiple caps, exclamation marks, etc.)
        if count_caps(turn.text) > len(turn.text) * 0.3:  # >30% caps
            emotional_escalation = True

    if trigger_phrase_count >= 2 or emotional_escalation:
        return EscalationAlert(
            is_escalating=True,
            triggers_detected=trigger_phrase_count,
            recommendation="Pause and refocus on unmet needs, not the surface issue"
        )

    return EscalationAlert(is_escalating=False)
```

### Luna's Mid-Session Interventions

```python
async def intervene_if_needed(
    conversation: List[Turn],
    context: MediationContext
) -> Optional[LunaIntervention]:
    """
    If conversation is escalating, Luna proactively intervenes.
    """

    alert = await detect_escalation_in_realtime(conversation, context)

    if alert.is_escalating:
        return LunaIntervention(
            type="pause_and_refocus",
            message=f"""
I notice we're getting tense again.

Let me pause here. I see a pattern:
- Yesterday's {context.unresolved_issues[0]['topic']} wasn't fully resolved
- Today it's showing up again as {context.current_conflict['topic']}

This keeps happening because the real issue is: {context.chronic_needs[0]['need']}

Before we go further, let's address that. What would it look like for you both to feel {context.chronic_needs[0]['need']}?
""",
            action="pause_for_reflection"
        )

    return None
```

---

## 3.4 Repair Plan Personalization

### Context-Aware Repair Plans

```python
async def generate_personalized_repair_plan(
    conflict_id: UUID,
    context: MediationContext
) -> RepairPlan:
    """
    Generate repair plan that addresses ROOT issues, not just surface conflict.
    """

    base_plan = await existing_repair_generation(conflict_id)

    # Enhance with pattern awareness
    plan = RepairPlan()

    # Step 1: Acknowledge the pattern
    plan.steps.append(RepairStep(
        order=1,
        action="acknowledge_pattern",
        description=f"""
Start with: "I realize we keep having versions of the same fight about {context.chronic_needs[0]['need']}."

This shows you understand the real issue.
""",
        speaker="both"
    ))

    # Step 2: Address unresolved issues
    if context.unresolved_issues:
        plan.steps.append(RepairStep(
            order=2,
            action="resolve_unresolved",
            description=f"""
Before moving forward, resolve: {context.unresolved_issues[0]['topic']} ({context.unresolved_issues[0]['days_unresolved']} days ago)

Why: You can't fix today's fight while that's still festering.
""",
            speaker="both"
        ))

    # Step 3: Address chronic need directly
    if context.chronic_needs:
        plan.steps.append(RepairStep(
            order=3,
            action="address_chronic_need",
            description=f"""
The core request: "{context.chronic_needs[0]['need'].replace('_', ' ')}"

Have conversation: "What would help you feel more {context.chronic_needs[0]['need'].replace('_', ' ')}?"
""",
            speaker="both"
        ))

    return plan
```

---

## 3.5 Implementation Details

### Update `agent.py` (Luna's Core)

```python
class RAGMediator:
    async def initialize_session(self, relationship_id: UUID):
        """Build context at session start."""
        self.mediation_context = await build_mediation_context(relationship_id)
        self.system_prompt = build_luna_system_prompt(self.mediation_context)

    async def process_user_message(self, message: str) -> str:
        """Process message with context awareness."""
        # Detect patterns
        detected = detect_trigger_patterns(message, self.mediation_context)

        # Generate response
        response = await generate_luna_response(
            message,
            self.mediation_context,
            self.conversation_history
        )

        # Check for escalation
        alert = await detect_escalation_in_realtime(
            self.conversation_history,
            self.mediation_context
        )
        if alert.is_escalating:
            intervention = await intervene_if_needed(
                self.conversation_history,
                self.mediation_context
            )
            response = intervention.message

        return response
```

### New Utility Functions

```python
# pattern_detection.py
def detect_trigger_patterns(text: str, context: MediationContext) -> List[Dict]:
    """Find trigger phrases in user's message."""

def identify_relevant_unresolved(text: str, context: MediationContext) -> List[Dict]:
    """Find connections to unresolved issues."""

def count_caps(text: str) -> int:
    """Count uppercase letters for emotional intensity detection."""
```

---

## 3.6 Implementation Checklist

- [ ] Create `build_mediation_context()` function
- [ ] Build Luna's context-aware system prompt template
- [ ] Implement trigger pattern detection during conversation
- [ ] Implement unresolved issue detection
- [ ] Create real-time escalation detection
- [ ] Build Luna's intervention system
- [ ] Update repair plan generation to use context
- [ ] Add context injection to agent initialization
- [ ] Test with sample conversations
- [ ] Verify Luna references patterns correctly

---

## 3.7 Testing Strategy

### Unit Tests

```python
def test_build_mediation_context():
    # Should load all relevant context data
    context = await build_mediation_context(relationship_id)
    assert context.unresolved_issues
    assert context.chronic_needs
    assert context.high_impact_triggers

def test_detect_trigger_patterns():
    # Should find trigger phrases in text
    text = "You didn't do that yesterday"
    context = MediationContext(
        high_impact_triggers=[{"phrase": "You didn't do that yesterday"}]
    )
    triggers = detect_trigger_patterns(text, context)
    assert len(triggers) > 0

def test_escalation_detection():
    # Should detect escalating conversation
    conversation = [
        Turn(speaker="a", text="You NEVER listen!!!"),
        Turn(speaker="b", text="THAT'S NOT TRUE"),
    ]
    alert = await detect_escalation_in_realtime(conversation, context)
    assert alert.is_escalating
```

### Integration Tests

1. Start mediation session → context should load correctly
2. User references past conflict → Luna should connect it
3. Escalation detected → Luna should intervene
4. Generate repair plan → should address chronic needs

### Manual Testing

1. Have real conversation with Luna
2. Verify she references specific unresolved issues
3. Check that trigger phrases are recognized
4. Confirm repair plan addresses root causes

---

## 3.8 Success Criteria

- Luna correctly identifies parent conflicts 80%+ of the time
- Luna's interventions prevent escalation 70%+ of the time
- Context-aware responses feel more relevant and empathetic
- Users report Luna "understanding the real issue" more often
- Repair plan adherence increases 40%+ compared to generic plans

---

## Next Steps

Once Phase 3 is complete, proceed to **Phase 4: Dashboard Visualization** to show couples what's happening.
