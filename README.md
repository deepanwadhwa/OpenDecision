<div align="center">

<h1>OpenDecision</h1>

<p>Open-source semantic decisions for structured state and documents.</p>

<p>
  <a href="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://pypi.org/project/OpenDecision/"><img alt="Version" src="https://img.shields.io/pypi/v/OpenDecision?label=version&color=2563eb"></a>
  <a href="https://pypi.org/project/OpenDecision/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/OpenDecision?color=2563eb"></a>
  <a href="https://github.com/deepanwadhwa/OpenDecision/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/OpenDecision?color=2563eb"></a>
  <a href="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/docs.yml"><img alt="Documentation" src="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/docs.yml/badge.svg"></a>
</p>

<p>
  <a href="https://deepanwadhwa.github.io/OpenDecision/">Documentation</a> ·
  <a href="#play-doom">Doom demo</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="#api-surface">API</a> ·
  <a href="https://deepanwadhwa.github.io/OpenDecision/examples/">Examples</a>
</p>

</div>

OpenDecision is the open-source equivalent of [TypeSafe's Jev](https://docs.typesafe.ai/introduction).

Send it application state or a document and typed questions. It returns structured answers that code can use directly.

Jev and OpenDecision use the same core pattern: state plus typed questions in, structured answers out. Both provide `Choice`, `Noul`, and `Score`.

OpenDecision provides:

- `Choice` to select one option from a list.
- `Noul` to measure whether a statement is true.
- `Score` to place state on an ordered scale.
- `Relation` to report `supports`, `contradicts`, `unknown`, or `conflicted`.
- Document processing with evidence retrieval and source passages.
- A Python API, a FastAPI server, and a TypeSafe SDK compatible endpoint.

The default backend is [`MoritzLaurer/ModernBERT-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0). [`MoritzLaurer/deberta-v3-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0) is an optional model. Both run locally and produce classification scores without generating text. See [model selection and evaluation](https://deepanwadhwa.github.io/OpenDecision/model-selection/) for the measured tradeoffs.

OpenDecision is licensed under Apache 2.0.

## What can it do?

### Play Doom

OpenDecision can choose actions for a bot in ViZDoom's Deadly Corridor at wall-clock speed.

The input is structured game state: health, ammo, kills, target position, goal position, and recent damage. The demo uses a disclosed tactical router, a target-tracking actuator, and a one-tic damage reflex. OpenDecision chooses between the actions available in the current tactical situation.

[![OpenDecision plays Doom at skill 5](https://raw.githubusercontent.com/deepanwadhwa/OpenDecision/main/demos/doom/opendecision-doom-skill5-preview.gif)](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill5-hero.mp4)

[Watch skill 1](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill1.mp4) · [Watch skill 3](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill3.mp4) · [Run the demo](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/README.md)

These are fixed-seed recordings. No win rate has been measured.

### Answer questions about data and documents

OpenDecision accepts plain text, JSON, or other Python values as state. The document API splits long documents, finds relevant passages, answers each question, and returns the passages used.

#### Insurance claim example

The sample claim contains a demand letter, policy facts, a police report, medical records, bills, and employer records.

| Question | Answer |
| --- | --- |
| Are the medical expenses documented? | `established` |
| Is a serious injury documented? | `refuted` |
| Is the rental need fully supported? | `unknown` |
| Are documents still outstanding? | `established` |

The current synthetic claim experiment retrieves all 17 required facts and matches all 10 composed decisions. This is one development case. See the [insurance claim benchmark](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/insurance_claim/README.md).

#### GDPR example

The GDPR example uses a 54,171-character document split into 31 sections.

| Question | Answer |
| --- | --- |
| Must a personal data breach be reported within 72 hours? | `true` |
| Must every organization appoint a Data Protection Officer? | `false` |
| Can pre-ticked boxes count as valid consent? | `false` |
| What is the maximum fine for serious infringements? | `EUR 20 million or 4% of worldwide turnover` |

The current retrieval experiment answers 9 of 10 objective questions correctly. See the [questions](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/gdpr_wiki/questions.py) and [saved results](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/gdpr_wiki_retrieved.json).

#### Yes/no answer modes

`POST /v1/documents/decide` has one `noul_mode` setting:

| Mode | Result |
| --- | --- |
| `binary` | Always chooses `true` or `false`. |
| `three_way` | Returns `supports`, `contradicts`, or `unknown`. |
| `both` | Runs both evaluations. This is the default. |

In `both` mode, OpenDecision reports `confirmed`, `tentative`, or `conflicted`. A conflict has `answer: null`. Both score distributions remain in the response.

These modes are for document `Noul` questions. They are separate from the internal scoring used by `Choice`.

## Get started

OpenDecision requires Python 3.13 or later.

```bash
pip install OpenDecision
```

Or add it to a `uv` project:

```bash
uv add OpenDecision
```

Run a decision in Python:

```python
from opendecision import OpenDecisionEngine

engine = OpenDecisionEngine()

result = engine.choice(
    state="The customer was charged twice for one subscription.",
    instructions="Which team should handle this request?",
    criteria={
        "billing": "Payments, invoices, refunds, and duplicate charges",
        "technical": "Software bugs and integration problems",
        "sales": "Pricing and new purchases",
    },
)

print(result["choice"])
# billing
```

Start the API:

```bash
opendecision serve
```

In a `uv` project, run `uv run opendecision serve`.

Open `http://127.0.0.1:8000/docs` to send requests from the interactive API page.

The model downloads from Hugging Face on first use.

## Documentation

- [Documentation index](https://deepanwadhwa.github.io/OpenDecision/)
- [Quick start and API](https://deepanwadhwa.github.io/OpenDecision/quickstart/)
- [Choice, Noul, Score, and Relation](https://deepanwadhwa.github.io/OpenDecision/primitives/)
- [Documents, evidence, and yes/no modes](https://deepanwadhwa.github.io/OpenDecision/document-decisions/)
- [Evidence relations and rules](https://deepanwadhwa.github.io/OpenDecision/evidence-and-rules/)
- [Doom demo](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/README.md)
- [Benchmarks](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/opendecision_original/README.md)
- [Model selection and evaluation](https://deepanwadhwa.github.io/OpenDecision/model-selection/)

## API surface

```text
GET  /health
POST /v1/systemone
POST /v1/documents/decide
GET  /docs
GET  /openapi.json
```

`POST /v1/systemone` accepts the core TypeSafe request shape. A local OpenDecision server can be used as the `base_url` for compatible clients.

## Current status

OpenDecision v0.1.2 is a developer preview.

Treat the model scores as uncalibrated. Evaluate the model and thresholds on your own data before using the results in an automated decision process.
