# OpenDecision

OpenDecision answers typed questions about application state and documents. It runs a local natural language inference model and returns structured values.

OpenDecision is an open-source equivalent of [TypeSafe's Jev](https://docs.typesafe.ai/introduction). Both use the same basic request pattern: provide state and typed questions, then receive structured answers.

## Install

With `pip`:

```bash
pip install OpenDecision
```

With `uv`:

```bash
uv add OpenDecision
```

[Continue to the get started guide](quickstart.md)

## What it provides

| Type | Use | Result |
| --- | --- | --- |
| `Choice` | Select one option. | Option name and probabilities |
| `Noul` | Test one statement. | A score from 0 to 1 |
| `Score` | Use an ordered scale. | Weighted score and probabilities |
| `Relation` | Compare evidence with a statement and its opposite. | `supports`, `contradicts`, `unknown`, or `conflicted` |
| Document decisions | Ask questions about text or JSON. | Answers and source passages |

[See code examples for each primitive](primitives.md)

## Start here

- [Get started](quickstart.md): install the package, run a Python example, and start the API.
- [Primitives](primitives.md): use `Choice`, `Noul`, `Score`, and `Relation`.
- [Document decisions](document-decisions.md): ask questions about long text or JSON and select a yes/no mode.
- [Evidence and rules](evidence-and-rules.md): rank evidence and combine facts with rules.
- [Examples](examples.md): run the Doom demo and review the insurance and GDPR examples.

## Interfaces

| Interface | Use |
| --- | --- |
| Python | Call OpenDecision in the same process as the application. |
| `POST /v1/systemone` | Send state and typed questions to the API. |
| `POST /v1/documents/decide` | Send a document and typed questions to the API. |
| TypeSafe-compatible endpoint | Use a compatible TypeSafe SDK client with a local server. |

## Basic example

```python
from opendecision import OpenDecisionEngine

engine = OpenDecisionEngine()

result = engine.choice(
    state="The customer was charged twice.",
    instructions="Which team should handle this request?",
    criteria={
        "billing": "Payments, invoices, refunds, and duplicate charges",
        "technical": "Software bugs",
        "sales": "Pricing and purchases",
    },
)

print(result["choice"])
# billing
```
