OpenDecision

[![Tests](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml/badge.svg)](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Model](https://img.shields.io/badge/backend-ModernBERT--large-6f42c1)

OpenDecision is an open-source semantic decision engine.

It takes a state, a natural-language question, and user-defined criteria, then returns a structured decision with probabilities.

The current backend is MoritzLaurer/ModernBERT-large-zeroshot-v2.0.

OpenDecision currently supports three primitives:

Choice — select one option from a set of user-defined alternatives.

Noul — evaluate a binary natural-language predicate.

Score — score a state against an ordered rubric.

It also exposes a /v1/systemone endpoint compatible with the core request/response flow used by the TypeSafe Python SDK.

Example

Request

{
  "state": "My credit card was charged twice for the same subscription.",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which department should handle this?",
      "criteria": {
        "billing": "Payments, invoices, refunds, and subscription charges",
        "technical": "Software bugs and integration problems",
        "sales": "Pricing and new purchases"
      }
    }
  }
}

Response

{
  "model": "modernbert-large-zeroshot-v2",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "billing",
      "probabilities": {
        "billing": 0.78,
        "technical": 0.05,
        "sales": 0.17
      },
      "confidence": 0.41
    }
  },
  "usage": {
    "input_tokens": 89,
    "output_tokens": 0
  }
}

Installation

OpenDecision uses uv.

git clone https://github.com/deepanwadhwa/OpenDecision.git
cd OpenDecision
uv sync

Run the server

uv run uvicorn opendecision.api.app:app \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000

Health check:

curl http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok",
  "service": "OpenDecision"
}

Interactive API documentation:

http://127.0.0.1:8000/docs

OpenAPI schema:

http://127.0.0.1:8000/openapi.json

Direct Python usage

from opendecision.engine import OpenDecisionEngine

engine = OpenDecisionEngine()

result = engine.choice(
    state="My internet stopped working after a power outage.",
    instructions="Who should this person contact first?",
    criteria={
        "isp": "Internet provider responsible for internet service",
        "power_utility": "Company responsible for electrical service",
        "router_manufacturer": "Company that manufactured the networking hardware",
    },
)

print(result)

Choice

Choice selects one option from a set of user-defined alternatives.

result = engine.choice(
    state="My card was charged twice.",
    instructions="Which department should handle this?",
    criteria={
        "billing": "Payments, invoices, refunds, and charges",
        "technical": "Software and integration problems",
        "sales": "Pricing and purchasing",
    },
)

Example output:

{
    "type": "choice",
    "choice": "billing",
    "probabilities": {
        "billing": 0.91,
        "technical": 0.04,
        "sales": 0.05
    },
    "confidence": 0.68
}

Noul

Noul evaluates whether a natural-language predicate is supported by the state.

result = engine.noul(
    state="I need this fixed before my presentation in thirty minutes.",
    instructions="This request is time-sensitive.",
)

Example output:

{
    "type": "noul",
    "noul": 0.95
}

Explicit true/false definitions are also supported:

result = engine.noul(
    state=(
        "The account logged in from California and then "
        "from Germany ten minutes later."
    ),
    instructions="The login activity is suspicious.",
    criteria={
        "true": "The activity is inconsistent with normal account usage.",
        "false": "The activity is consistent with normal account usage.",
    },
)

Score

Score evaluates a state against an ordered rubric.

result = engine.score(
    state="This is ridiculous. I have contacted you five times already.",
    instructions="How frustrated is the customer?",
    criteria=[
        "Calm",
        "Frustrated",
        "Extremely angry",
    ],
)

Example output:

{
    "type": "score",
    "score": 1.82,
    "legend": {
        "0": "Calm",
        "1": "Frustrated",
        "2": "Extremely angry"
    },
    "probabilities": {
        "0": 0.03,
        "1": 0.12,
        "2": 0.85
    },
    "confidence": 0.61
}

The returned score is the probability-weighted position in the rubric.

TypeSafe SDK compatibility

OpenDecision implements the core /v1/systemone request and response format used by the TypeSafe Python SDK.

The official client can be pointed at a local OpenDecision server:

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(
    api_key="local",
    base_url="http://127.0.0.1:8000",
)

response = client.system_one(
    state="I was charged twice and need this fixed before my meeting.",
    questions={
        "department": Choice(
            instructions="Which department should handle this?",
            criteria={
                "billing": "Payments and refunds",
                "technical": "Software problems",
                "sales": "Purchasing questions",
            },
        ),
        "urgent": Noul(
            instructions="This request is time-sensitive.",
        ),
        "frustration": Score(
            instructions="How frustrated is the customer?",
            criteria=[
                "Calm",
                "Frustrated",
                "Extremely angry",
            ],
        ),
    },
)

print(response)

OpenDecision is an independent open-source project and is not affiliated with TypeSafe.

Current model

Default backend:

MoritzLaurer/ModernBERT-large-zeroshot-v2.0

Current properties:

approximately 400M parameters

zero-shot natural-language classification

user-defined labels at inference time

ModernBERT architecture

up to 8192-token model context

Apache-2.0 model license

The backend is intended to be model-independent. ModernBERT is the first supported backend.

Decision compilation

OpenDecision uses different NLI formulations for different decision primitives.

Choice

state + question
→ semantic candidate descriptions
→ zero-shot classification

Noul

state
→ natural-language predicate
→ direct entailment probability

Score

state
→ question + rubric description hypotheses
→ probability distribution
→ weighted score

Using different formulations for the three primitives performed better than using one generic zero-shot formulation.

Evaluation

Run the current benchmark:

uv run python benchmarks/run_eval.py

Current seed benchmark:

Choice accuracy:  9/10 = 90.0%
Noul accuracy:    4/4  = 100.0%
Score MAE:              0.178
Total cases:      17

These numbers come from a small development benchmark and should not be interpreted as general model accuracy.

Current benchmark categories include:

customer support routing

internet troubleshooting

ambiguity

scientific classification

arbitrary invented labels

urgency

security

ordinal scoring

Run the compiler/template ablation benchmark:

uv run python benchmarks/template_ablation.py

Saved results are stored in:

benchmarks/results/

Tests

Run all tests:

uv run pytest -v

The current test suite covers:

Choice

Noul

Noul with explicit criteria

Score

structured state

arbitrary user-defined labels

HTTP API

multiple question types in one request

request validation

Confidence

confidence currently measures concentration of the returned probability distribution.

It is not the probability that the model is correct.

Empirical calibration is planned separately.

Known limitations

The current benchmark dataset is small.

Model probabilities are not yet empirically calibrated.

Zero-shot classification evaluates candidate hypotheses separately.

Large candidate sets increase inference cost.

Structured JSON is serialized into text before inference.

ModernBERT can still make incorrect semantic decisions even when the correct option is present.

Long-context behavior has not yet been evaluated systematically.

Project status

Milestone

Status

Description

M0

Complete

Raw ModernBERT zero-shot baseline

M1

Complete

Choice, Noul, and Score primitives

M2

Complete

/v1/systemone HTTP API

M3

Complete

TypeSafe Python SDK compatibility

M4

Active

Evaluation and compiler benchmarking

Planned work includes:

larger evaluation corpus

additional zero-shot backends

ONNX inference

CPU and GPU benchmarks

dynamic batching

probability calibration

long-context evaluation

confidential-compute deployment

custom classifier training

shared-state multi-question inference

Repository structure

OpenDecision/
├── benchmarks/
│   ├── cases.jsonl
│   ├── run_eval.py
│   ├── template_ablation.py
│   └── results/
├── examples/
├── src/
│   └── opendecision/
│       ├── engine.py
│       └── api/
├── tests/
├── pyproject.toml
└── README.md

License

See LICENSE.