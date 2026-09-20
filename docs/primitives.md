# Primitives

OpenDecision provides four question types. The first three match the core TypeSafe Jev primitives. `Relation` adds an evidence judgment with an explicit opposite statement.

| Type | Use it for | Main result |
| --- | --- | --- |
| `Choice` | Select one option from a list. | Option name, probabilities, confidence |
| `Noul` | Measure whether one statement is true. | A value from 0 to 1 |
| `Score` | Place state on an ordered scale. | Weighted score, probabilities, confidence |
| `Relation` | Compare evidence with a proposition and its opposite. | `supports`, `contradicts`, `unknown`, or `conflicted` |

## Choice

Use `Choice` when the answer must be one named option.

```python
result = engine.choice(
    state="The customer was charged twice for one subscription.",
    instructions="Which team should handle this request?",
    criteria={
        "billing": "Payments, invoices, refunds, and duplicate charges",
        "technical": "Software bugs and integration problems",
        "sales": "Pricing and new purchases",
    },
)
```

Response shape:

```python
{
    "type": "choice",
    "choice": "billing",
    "probabilities": {
        "billing": 0.91,
        "technical": 0.06,
        "sales": 0.03,
    },
    "confidence": 0.68,
}
```

The values above only show the response shape.

`confidence` is based on the concentration of the returned distribution. Treat it as uncalibrated.

### Standard and fast Choice

`engine.choice()` runs two fixed NLI formulations. When they select different options, it runs a small adjudication over those two options.

`engine.choice_fast()` runs one formulation. Use it when latency matters more than the extra comparison.

The older README called the two internal formulations Compiler A and Compiler B. They are still used by `engine.choice()`. They are implementation details and have no public configuration setting.

The `binary`, `three_way`, and `both` settings belong to document `Noul` questions. They do not change `Choice`.

## Noul

Use `Noul` to measure support for one statement.

```python
result = engine.noul(
    state="The production service is currently unavailable.",
    instructions="This incident is time-sensitive.",
)

print(result["noul"])
```

Response shape:

```python
{
    "type": "noul",
    "noul": 0.87,
}
```

The result is an entailment score from 0 to 1.

Use explicit criteria when the meaning of true and false must be stated exactly:

```python
result = engine.noul(
    state="The login came from California and Germany ten minutes apart.",
    instructions="Is this login activity suspicious?",
    criteria={
        "true": "The activity is inconsistent with normal account usage.",
        "false": "The activity is consistent with normal account usage.",
    },
)
```

The document API can turn `Noul` into a boolean or a three-way evidence judgment. See [Document decisions](document-decisions.md).

## Score

Use `Score` for an ordered rubric. Criteria are ordered from index 0 upward.

```python
result = engine.score(
    state="The application crashes for every user at startup.",
    instructions="How severe is this software bug?",
    criteria=[
        "Cosmetic or negligible impact",
        "Minor impact with an easy workaround",
        "Important workflow is degraded",
        "Critical workflow is unavailable",
    ],
)
```

Response shape:

```python
{
    "type": "score",
    "score": 2.74,
    "legend": {
        "0": "Cosmetic or negligible impact",
        "1": "Minor impact with an easy workaround",
        "2": "Important workflow is degraded",
        "3": "Critical workflow is unavailable",
    },
    "probabilities": {
        "0": 0.01,
        "1": 0.04,
        "2": 0.15,
        "3": 0.80,
    },
    "confidence": 0.47,
}
```

The values above only show the response shape. `score` is the probability-weighted average of the criterion indices.

## Relation

Use `Relation` when an application must distinguish missing evidence from contrary evidence.

```python
result = engine.relation(
    state="The supplier certificate expired on April 1, 2026.",
    proposition="The supplier certificate is expired.",
    contradiction="The supplier certificate is current.",
)
```

Response shape for a native three-way NLI model:

```python
{
    "type": "relation",
    "relation": "supports",
    "scores": {
        "supports": 0.94,
        "contradicts": 0.02,
        "unknown": 0.04,
    },
    "backend": "native_nli",
}
```

A native three-way NLI model returns `supports`, `contradicts`, or `unknown`.

A binary entailment backend scores the proposition and its explicit opposite separately. It can return `supports`, `contradicts`, `conflicted`, or `unknown` according to the selected threshold.

## Use several primitives in one API request

`POST /v1/systemone` accepts a dictionary of questions. Each question can use a different primitive.

```json
{
  "state": "The customer was charged twice and needs help today.",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this?",
      "criteria": {
        "billing": "Payment and refund requests",
        "technical": "Software problems"
      }
    },
    "urgent": {
      "type": "noul",
      "instructions": "This request is time-sensitive."
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated is the customer?",
      "criteria": ["Calm", "Frustrated", "Very angry"]
    }
  }
}
```
