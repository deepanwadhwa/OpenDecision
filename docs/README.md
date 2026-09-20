# OpenDecision documentation

OpenDecision turns state and typed questions into structured answers.

## Start here

- [Quick start and API](quickstart.md) covers installation, Python usage, the server, and model selection.
- [Primitives](primitives.md) explains `Choice`, `Noul`, `Score`, and `Relation` with examples and response shapes.
- [Document decisions](document-decisions.md) explains document splitting, evidence retrieval, citations, and the `binary`, `three_way`, and `both` modes.
- [Evidence and rules](evidence-and-rules.md) explains evidence relations, relevance ranking, and deterministic rule composition.
- [Doom demo](../demos/doom/README.md) explains the real-time ViZDoom example.
- [Publishing](publishing.md) covers versioning, PyPI Trusted Publishing, and releases.

## Choose an interface

### Python

Use `OpenDecisionEngine` when the application runs in the same Python process.

```python
from opendecision.engine import OpenDecisionEngine

engine = OpenDecisionEngine()
```

### System One API

Use `POST /v1/systemone` to send one state value and one or more typed questions.

The endpoint supports `choice`, `noul`, `score`, and `relation` questions. Its request and response structure is compatible with the core TypeSafe SDK flow.

### Document API

Use `POST /v1/documents/decide` for long text or JSON documents. The endpoint finds relevant evidence and includes it with each answer.

## Main concepts

### State

State is the input being evaluated. It can be a string, a dictionary, a list, a JSON document, or another JSON-serializable Python value.

### Question

A question defines one decision. Its type controls the answer shape.

### Criteria

Criteria describe the valid answers. `Choice` uses named options. `Score` uses an ordered list. `Noul` can use explicit true and false statements. `Relation` always uses a proposition and its explicit opposite.

### Evidence

The document API returns the document passages used for each decision. Each passage includes an ID, text, and relevance score.

### Rules

Rules combine fact statuses with `all`, `any`, and `not`. The output contains a trace of every fact and operation.

## Source map

| Component | File |
| --- | --- |
| Core engine | [`src/opendecision/engine.py`](../src/opendecision/engine.py) |
| API schemas | [`src/opendecision/api/schemas.py`](../src/opendecision/api/schemas.py) |
| API routes | [`src/opendecision/api/app.py`](../src/opendecision/api/app.py) |
| Document service | [`src/opendecision/documents.py`](../src/opendecision/documents.py) |
| Evidence backend | [`src/opendecision/evidence.py`](../src/opendecision/evidence.py) |
| Rule evaluation | [`src/opendecision/rules.py`](../src/opendecision/rules.py) |
