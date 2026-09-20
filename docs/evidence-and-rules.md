# Evidence and rules

OpenDecision separates semantic evidence judgments from application rules.

The model determines the relationship between text and a proposition. Application code determines how several facts combine into a decision.

## Evidence relations

```python
result = engine.relation(
    state="Cervical spine X-ray: No acute fracture or dislocation.",
    proposition="The X-ray found no acute fracture or dislocation.",
    contradiction="The X-ray found an acute fracture or dislocation.",
)
```

Possible relations:

| Relation | Meaning |
| --- | --- |
| `supports` | The evidence supports the proposition. |
| `contradicts` | The evidence supports the explicit opposite. |
| `unknown` | The evidence establishes neither statement. |
| `conflicted` | A binary backend finds support for both statements. |

The application supplies both the proposition and its opposite. This makes the tested meaning visible in code and responses.

## Batch relations

Use `engine.relations()` to evaluate several evidence items:

```python
results = engine.relations(
    items=[
        {
            "state": "The invoice total is $3,250.",
            "proposition": "The invoice total is $3,250.",
            "contradiction": "The invoice total differs from $3,250.",
        },
        {
            "state": "The pickup date is still pending.",
            "proposition": "The rental pickup date is confirmed.",
            "contradiction": "The rental pickup date was cancelled.",
        },
    ]
)
```

## Rank evidence

Use `engine.rank_evidence()` when a document is already split into evidence units:

```python
ranked = engine.rank_evidence(
    evidence=[
        {"id": "policy", "text": "Collision coverage is active."},
        {"id": "invoice", "text": "The repair estimate is $3,250."},
    ],
    proposition="Collision coverage is active.",
    contradiction="Collision coverage is inactive.",
    top_k=1,
)
```

The ranker checks semantic relevance. It also preserves exact numeric anchors from the proposition. Callers can supply more anchors for dates, identifiers, citations, or domain terms.

## Compose facts with rules

Convert evidence relations to rule statuses:

```python
from opendecision.rules import relation_status

status = relation_status("supports")
# established
```

The mapping is:

| Evidence relation | Rule status |
| --- | --- |
| `supports` | `established` |
| `contradicts` | `refuted` |
| `conflicted` | `conflicted` |
| `unknown` | `unknown` |

Combine statuses with `all`, `any`, and `not`:

```python
from opendecision.rules import evaluate_rule

facts = {
    "police_rear_impact": "established",
    "witness_rear_impact": "established",
    "pickup_confirmation": "unknown",
}

result = evaluate_rule(
    {"any": ["police_rear_impact", "witness_rear_impact"]},
    facts,
)
```

Response:

```python
{
    "op": "any",
    "status": "established",
    "children": [
        {
            "op": "fact",
            "fact": "police_rear_impact",
            "status": "established",
        },
        {
            "op": "fact",
            "fact": "witness_rear_impact",
            "status": "established",
        },
    ],
}
```

The trace records each input and operation used to reach the status.

## Backend contract

`OpenDecisionEngine` delegates relations and relevance ranking to an `EvidenceBackend`.

The bundled `NliEvidenceBackend` supports:

- Native three-way NLI models with entailment, contradiction, and neutral labels.
- Binary entailment models with an explicit opposite statement.
- Batched relation scoring.
- Evidence ranking.
- Exact anchors.

Applications can assign another backend to `engine.evidence_backend` while keeping the same engine methods.
