# Phase 2: Intelligence & Pattern Detection

**Goal**: Build analytics on enriched conflict data to identify patterns and escalation risks

**Timeline**: 2-3 weeks

**Deliverables**:
- Trigger phrase analytics queries
- Escalation risk scoring
- Pattern recognition algorithms
- New analytics endpoints

**Depends On**: Phase 1 (Data Capture & Enrichment)

---

## 2.1 Trigger Phrase Analytics

### Query: Most Impactful Trigger Phrases

Find phrases that correlate with escalation:

```sql
SELECT
  phrase,
  phrase_category,
  COUNT(*) as usage_count,
  AVG(emotional_intensity) as avg_intensity,
  COUNT(CASE WHEN is_escalation_trigger THEN 1 END)::FLOAT / COUNT(*) as escalation_rate,
  AVG(CASE WHEN tp.conflict_id = c.id AND c.resentment_level > 7 THEN 1 ELSE 0 END) as high_resentment_correlation
FROM trigger_phrases tp
JOIN conflicts c ON tp.conflict_id = c.id
WHERE tp.relationship_id = $1
GROUP BY phrase, phrase_category
ORDER BY escalation_rate DESC, avg_intensity DESC
LIMIT 20;
```

### Query: Phrase Frequency Trends

Track how often phrases are used over time:

```sql
SELECT
  DATE_TRUNC('week', tp.created_at) as week,
  phrase,
  COUNT(*) as usage_count
FROM trigger_phrases tp
WHERE tp.relationship_id = $1
GROUP BY DATE_TRUNC('week', tp.created_at), phrase
ORDER BY week DESC, usage_count DESC;
```

### Query: Speaker-Specific Patterns

Identify if one partner uses certain trigger phrases more:

```sql
SELECT
  speaker,
  phrase,
  COUNT(*) as usage_count,
  AVG(emotional_intensity) as avg_intensity
FROM trigger_phrases
WHERE relationship_id = $1
GROUP BY speaker, phrase
ORDER BY speaker, usage_count DESC;
```

---

## 2.2 Escalation Risk Scoring

### Escalation Risk Algorithm

```python
def calculate_escalation_risk(relationship_id: UUID) -> EscalationRiskReport:
    """
    Calculate the likelihood of conflict escalation in next 7 days.

    Factors:
    1. Unresolved issues count (weight: 0.4)
    2. Resentment accumulation rate (weight: 0.3)
    3. Days since last conflict (weight: 0.2)
    4. Recurrence pattern (weight: 0.1)
    """

    # Factor 1: Count unresolved issues
    unresolved_count = db.get_unresolved_conflicts(relationship_id)
    unresolved_score = min(unresolved_count / 5.0, 1.0)  # 5+ unresolved = max score

    # Factor 2: Resentment accumulation
    recent_conflicts = db.get_recent_conflicts(relationship_id, days=30)
    avg_resentment = mean([c.resentment_level for c in recent_conflicts])
    resentment_score = avg_resentment / 10.0

    # Factor 3: Time since last conflict
    days_since_last = calculate_days_since(recent_conflicts[-1].created_at)
    time_score = 1.0 - (days_since_last / 30.0)  # recent conflicts = higher score

    # Factor 4: Recurrence pattern
    if has_rapid_recurrence_pattern(recent_conflicts):
        recurrence_score = 0.8
    else:
        recurrence_score = 0.3

    # Weighted score
    risk_score = (
        unresolved_score * 0.4 +
        resentment_score * 0.3 +
        time_score * 0.2 +
        recurrence_score * 0.1
    )

    return EscalationRiskReport(
        risk_score=risk_score,  # 0.0-1.0
        interpretation=interpret_score(risk_score),  # 'low', 'medium', 'high', 'critical'
        unresolved_issues=unresolved_count,
        days_until_predicted_conflict=predict_next_conflict(recent_conflicts),
        recommendations=generate_recommendations(risk_score, recent_conflicts)
    )
```

### Interpretation Guide

```
0.0 - 0.25: Low Risk
  - Healthy pattern
  - Recommend: Regular check-ins with Luna

0.25 - 0.50: Medium Risk
  - Some unresolved issues
  - Recommend: Address 1-2 unresolved items this week

0.50 - 0.75: High Risk
  - Multiple unresolved issues + recent conflicts
  - Recommend: Prioritize resolution with Luna; set aside dedicated time

0.75 - 1.0: Critical Risk
  - Rapid recurrence + high resentment
  - Recommend: Immediate mediation session with Luna
```

---

## 2.3 Pattern Recognition

### Pattern: Conflict Chains

Identify sequences of related conflicts:

```python
def identify_conflict_chains(relationship_id: UUID) -> List[ConflictChain]:
    """
    Find patterns where one conflict triggers another.

    Example: [Unheard] → [Trust] → [Communication] → [Door Issue]
    """

    conflicts = db.get_all_conflicts(relationship_id)
    chains = []

    for i, conflict in enumerate(conflicts):
        if conflict.parent_conflict_id:
            chain = trace_chain_backwards(conflict)
            if len(chain) >= 2:  # Only sequences of 2+
                chains.append(ConflictChain(
                    conflicts=chain,
                    root_cause=chain[0].topic,
                    surface_issue=conflict.topic,
                    unmet_needs=aggregate_needs(chain),
                    resolution_attempts=count_resolutions(chain)
                ))

    return chains
```

### Pattern: Unmet Needs Recurrence

Track which needs appear across multiple conflicts:

```sql
SELECT
  need,
  COUNT(DISTINCT conflict_id) as conflict_count,
  MIN(first_identified_at) as first_appeared,
  COUNT(DISTINCT DATE(created_at)) as days_appeared_in,
  CASE WHEN COUNT(DISTINCT conflict_id) >= 3 THEN TRUE ELSE FALSE END as is_chronic
FROM unmet_needs
WHERE relationship_id = $1
GROUP BY need
ORDER BY conflict_count DESC;
```

### Pattern: Trigger Phrase Sequences

Find phrases that often appear together in escalating conflicts:

```python
def find_trigger_phrase_sequences(relationship_id: UUID, window_size: int = 5) -> List[PhraseSequence]:
    """
    Find common sequences of trigger phrases within conflicts.

    Example: ["You didn't X yesterday"] → ["I didn't say anything"] → [escalation]
    """

    recent_conflicts = db.get_recent_conflicts(relationship_id, days=90)
    sequences = defaultdict(int)

    for conflict in recent_conflicts:
        phrases = sorted(conflict.trigger_phrases, key=lambda p: p.timestamp)
        for i in range(len(phrases) - window_size + 1):
            seq = tuple([p.phrase for p in phrases[i:i+window_size]])
            sequences[seq] += 1

    # Return sequences that appear 2+ times
    return [
        PhraseSequence(phrases=seq, frequency=count)
        for seq, count in sequences.items()
        if count >= 2
    ]
```

---

## 2.4 New Analytics Endpoints

### GET `/api/analytics/escalation-risk`

Returns escalation risk report:

```json
{
  "risk_score": 0.72,
  "interpretation": "high",
  "unresolved_issues": 3,
  "days_until_predicted_conflict": 4,
  "recommendations": [
    "Address the unresolved trust issue from conflict on Dec 18",
    "Both partners mentioned 'feeling unheard' - prioritize this",
    "Last 3 conflicts escalated within 5-7 days - pattern is accelerating"
  ]
}
```

### GET `/api/analytics/trigger-phrases`

Returns top trigger phrases with impact:

```json
{
  "most_impactful": [
    {
      "phrase": "You didn't do that yesterday",
      "category": "temporal_reference",
      "usage_count": 8,
      "avg_emotional_intensity": 8.2,
      "escalation_rate": 0.75,
      "speaker": "partner_b"
    },
    {
      "phrase": "I didn't say anything",
      "category": "passive_aggressive",
      "usage_count": 5,
      "avg_emotional_intensity": 7.6,
      "escalation_rate": 0.80,
      "speaker": "partner_a"
    }
  ],
  "trends": {
    "past_30_days": [
      { "week": "2024-12-01", "phrase": "You never listen", "count": 3 },
      { "week": "2024-12-08", "phrase": "You never listen", "count": 5 }
    ]
  }
}
```

### GET `/api/analytics/conflict-chains`

Returns identified conflict sequences:

```json
{
  "chains": [
    {
      "root_cause": "Communication breakdown",
      "conflicts_in_chain": 4,
      "timeline": "2024-11-15 → 2024-11-22 → 2024-12-01 → 2024-12-10",
      "unmet_needs": ["feeling_heard", "trust"],
      "resolution_attempts": 0,
      "recommendations": "This chain has never been fully resolved. Address root cause directly."
    }
  ]
}
```

### GET `/api/analytics/unmet-needs`

Track chronic unmet needs:

```json
{
  "chronic_needs": [
    {
      "need": "feeling_heard",
      "conflict_count": 7,
      "first_appeared": "2024-10-01",
      "days_appeared_in": 45,
      "impact": "high - appears in 70% of conflicts",
      "recommendations": "This is the core issue. Work on active listening and validation."
    }
  ]
}
```

---

## 2.5 Implementation Details

### New Service: `pattern_analysis_service.py`

```python
class PatternAnalysisService:
    async def calculate_escalation_risk(self, relationship_id: UUID) -> EscalationRiskReport:
        """Calculate escalation risk score and factors."""

    async def find_trigger_phrase_patterns(self, relationship_id: UUID) -> TriggerPhraseAnalysis:
        """Identify most impactful trigger phrases."""

    async def identify_conflict_chains(self, relationship_id: UUID) -> List[ConflictChain]:
        """Trace chains of related conflicts."""

    async def track_chronic_needs(self, relationship_id: UUID) -> List[ChronicNeed]:
        """Find unmet needs appearing in 3+ conflicts."""

    async def predict_next_conflict(self, relationship_id: UUID) -> ConflictPrediction:
        """Estimate when next conflict likely to occur."""
```

### New Routes: `analytics_pattern.py`

```python
@router.get("/api/analytics/escalation-risk")
async def get_escalation_risk(relationship_id: UUID) -> EscalationRiskReport:
    return await pattern_service.calculate_escalation_risk(relationship_id)

@router.get("/api/analytics/trigger-phrases")
async def get_trigger_phrases(relationship_id: UUID) -> TriggerPhraseAnalysis:
    return await pattern_service.find_trigger_phrase_patterns(relationship_id)

@router.get("/api/analytics/conflict-chains")
async def get_conflict_chains(relationship_id: UUID) -> List[ConflictChain]:
    return await pattern_service.identify_conflict_chains(relationship_id)
```

---

## 2.6 Implementation Checklist

- [ ] Create `pattern_analysis_service.py` with core algorithms
- [ ] Implement escalation risk scoring function
- [ ] Write SQL queries for trigger phrase analytics
- [ ] Implement conflict chain identification
- [ ] Create pattern detection for chronic needs
- [ ] Build prediction algorithm for next conflict
- [ ] Add new analytics endpoints
- [ ] Add database helper functions
- [ ] Write comprehensive tests for each algorithm
- [ ] Document all metrics and scoring logic

---

## 2.7 Testing Strategy

### Unit Tests

```python
def test_escalation_risk_multiple_unresolved():
    # 4 unresolved conflicts = high risk
    risk = calculate_escalation_risk(relationship_id)
    assert risk.risk_score > 0.5

def test_escalation_risk_recent_conflict():
    # Conflict yesterday + unresolved = higher risk
    risk = calculate_escalation_risk(relationship_id)
    assert risk.risk_score > 0.4

def test_identify_conflict_chains():
    # Chain of 3+ related conflicts should be identified
    chains = identify_conflict_chains(relationship_id)
    assert len(chains) > 0
    assert all(len(c.conflicts) >= 2 for c in chains)

def test_chronic_needs_identification():
    # Needs in 3+ conflicts marked as chronic
    needs = track_chronic_needs(relationship_id)
    chronic = [n for n in needs if n.is_chronic]
    assert all(n.conflict_count >= 3 for n in chronic)
```

### Integration Tests

1. Create 5 conflicts with overlapping unmet needs → should identify chronic need
2. Create conflict chain → should trace back correctly
3. Calculate escalation risk with various states → scores should reflect conditions
4. Query trigger phrases → results should match actual data

---

## 2.8 Success Criteria

- Escalation risk score is accurate (validated against actual escalations)
- Trigger phrase patterns correctly identify high-impact phrases
- Conflict chains are properly traced with no missing links
- Chronic needs identified with >85% accuracy
- All analytics endpoints perform <500ms with 30+ conflicts
- Predictions of next conflict within ±3 days 70% of the time

---

## Next Steps

Once Phase 2 is complete, proceed to **Phase 3: Luna's Awareness** to integrate these insights into mediation.
