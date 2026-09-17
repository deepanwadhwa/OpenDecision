# OpenDecision

[![Tests](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml/badge.svg)](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml)


OpenDecision is an open-source semantic decision engine.

It takes:

- a state, such as text or structured JSON
- a natural-language question
- user-defined criteria

and returns structured decisions and probability distributions.

OpenDecision currently uses [`MoritzLaurer/ModernBERT-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0) as its inference backend.

The current API implements three decision primitives:

- `Choice` — choose one option from a set
- `Noul` — evaluate a binary natural-language predicate
- `Score` — score a state against an ordered rubric

OpenDecision also exposes a `/v1/systemone` API compatible with the core request and response format used by the TypeSafe Python SDK.

## Example

Input:

```json
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

Example output:

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

OpenDecision currently uses uv.

Clone the repository:

git clone https://github.com/YOUR_USERNAME/OpenDecision.git
cd OpenDecision

Install dependencies:

uv sync
Run the server
uv run uvicorn opendecision.api.app:app \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000

Check the server:

curl http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok",
  "service": "OpenDecision"
}

Interactive API documentation is available at:

http://127.0.0.1:8000/docs
Python usage

OpenDecision can also be used directly without the HTTP server.

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

Example result:

{
    "type": "choice",
    "choice": "billing",
    "probabilities": {
        "billing": 0.91,
        "technical": 0.04,
        "sales": 0.05,
    },
    "confidence": 0.68,
}
Noul

Noul evaluates whether a natural-language predicate is supported by the state.

result = engine.noul(
    state="I need this fixed before my presentation in thirty minutes.",
    instructions="This request is time-sensitive.",
)

Example result:

{
    "type": "noul",
    "noul": 0.95,
}

Explicit true and false definitions are also supported:

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

Example result:

{
    "type": "score",
    "score": 1.82,
    "legend": {
        "0": "Calm",
        "1": "Frustrated",
        "2": "Extremely angry",
    },
    "probabilities": {
        "0": 0.03,
        "1": 0.12,
        "2": 0.85,
    },
    "confidence": 0.61,
}

The score is the probability-weighted position in the rubric.

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

OpenDecision is an independent open-source project and is not affiliated with TypeSafe.

Model

Current default model:

MoritzLaurer/ModernBERT-large-zeroshot-v2.0

Properties:

approximately 400M parameters
zero-shot natural-language classification
user-defined labels at inference time
ModernBERT architecture
up to 8192-token model context
Apache-2.0 model license

The backend is intended to become model-independent. ModernBERT is the first supported backend.

Compiler

OpenDecision uses different NLI formulations for different decision primitives.

Current implementation:

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
→ weighted probability distribution

This produced better results than using one generic zero-shot prompt for all three primitives.

Evaluation

Run the current benchmark:

uv run python benchmarks/run_eval.py

Current seed benchmark:

Choice accuracy:  9/10 = 90.0%
Noul accuracy:    4/4  = 100.0%
Score MAE:              0.178
Total cases:      17

These numbers are from a small development benchmark and should not be interpreted as general model accuracy.

The benchmark contains examples involving:

customer support routing
ambiguity
internet troubleshooting
scientific classification
arbitrary invented labels
urgency
security
ordinal scoring

Template/compiler experiments are stored in:

benchmarks/results/

Run the template ablation benchmark with:

uv run python benchmarks/template_ablation.py
Known limitations

OpenDecision currently has several limitations.

The benchmark dataset is small.
Model output probabilities are not yet empirically calibrated.
confidence measures concentration of the returned distribution. It is not the probability that the answer is correct.
Zero-shot classification requires evaluating candidate hypotheses separately.
Long inputs and large candidate sets can increase inference cost.
ModernBERT can make incorrect semantic decisions even when the correct option is present.
Structured JSON is currently serialized into text before inference.
Tests

Run all tests:

uv run pytest -v

Current test suite covers:

Choice
Noul
Noul with explicit criteria
Score
structured state
arbitrary user-defined labels
HTTP API
multi-question API requests
request validation
Project status
M0  Complete  Raw ModernBERT zero-shot baseline
M1  Complete  Choice, Noul, and Score primitives
M2  Complete  /v1/systemone HTTP API
M3  Complete  TypeSafe Python SDK compatibility
M4  Active    Evaluation and compiler benchmarking

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
└── pyproject.toml
License

See LICENSE.


For the green **Tests passing** badge, add this file:

```text
.github/workflows/tests.yml

with:

name: Tests

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run tests
        run: uv run pytest -v