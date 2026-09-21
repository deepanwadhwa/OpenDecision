---
hide:
  - navigation
  - toc
---

<div class="od-hero" markdown>

<span class="od-eyebrow">Open-source semantic decision engine</span>

# Decisions your code can use.

Send OpenDecision application state or a document and typed questions. Get structured answers, scores, confidence, and source evidence from a local NLI model.

<div class="od-actions">
  <a class="md-button md-button--primary" href="quickstart/">Get started</a>
  <a class="md-button" href="primitives/">Explore the primitives</a>
</div>

<div class="od-install" markdown>

```bash
pip install OpenDecision
```

</div>

</div>

<div class="od-card-grid" markdown>

<div class="od-card" markdown>

### Typed decisions

Use `Choice`, `Noul`, `Score`, and `Relation` to return values your application can branch on directly.

[Read about primitives](primitives.md)

</div>

<div class="od-card" markdown>

### Document questions

Split long text, retrieve relevant passages, and answer questions with the evidence included in every response.

[Read about documents](document-decisions.md)

</div>

<div class="od-card" markdown>

### Local model execution

Run the default ModernBERT NLI model on your own machine. Select another compatible model when needed.

[Configure a model](quickstart.md#select-a-model)

</div>

<div class="od-card" markdown>

### Auditable rules

Keep semantic evidence judgments separate from deterministic application policy. Every composed rule returns a trace.

[Read about evidence and rules](evidence-and-rules.md)

</div>

</div>

## One request, several decisions

Questions share the same state and keep separate response types.

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
    }
  }
}
```

## Interfaces

| Interface | Use it when |
| --- | --- |
| Python | OpenDecision runs in the same application process. |
| `POST /v1/systemone` | A service sends structured state and typed questions. |
| `POST /v1/documents/decide` | A service asks questions about long text or JSON documents. |
| TypeSafe-compatible endpoint | An existing TypeSafe SDK client needs a local OpenDecision server. |

[:material-arrow-right: Install and run OpenDecision](quickstart.md){ .md-button .md-button--primary }
