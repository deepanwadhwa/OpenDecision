# Quick start and API

## Requirements

- Python 3.13 or later
- `pip` or `uv`
- Enough memory to load the selected transformer model

## Install

With `pip`:

```bash
pip install OpenDecision
```

With `uv`:

```bash
uv add OpenDecision
```

## Use the Python engine

```python
from opendecision import OpenDecisionEngine

engine = OpenDecisionEngine()

answer = engine.choice(
    state={
        "plan": "enterprise",
        "message": "Please quote 200 additional seats.",
    },
    instructions="Which team should handle this request?",
    criteria={
        "billing": "Existing invoices and payment problems",
        "technical": "Software bugs and integrations",
        "sales": "Purchasing, pricing, and account expansion",
    },
)

print(answer["choice"])
# sales
```

`OpenDecisionEngine()` loads the default model. The model downloads from Hugging Face the first time it is used.

## Start the server

```bash
opendecision serve
```

In a `uv` project:

```bash
uv run opendecision serve
```

Available routes:

```text
GET  /health
POST /v1/systemone
POST /v1/documents/decide
GET  /docs
GET  /openapi.json
```

Use `http://127.0.0.1:8000/docs` to inspect the schemas and send requests.

## Send a System One request

```bash
curl http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  -d '{
    "state": "The customer was charged twice.",
    "questions": {
      "department": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
          "billing": "Payments, invoices, refunds, and duplicate charges",
          "technical": "Software bugs",
          "sales": "Pricing and purchases"
        }
      },
      "urgent": {
        "type": "noul",
        "instructions": "This request is urgent."
      }
    }
  }'
```

Questions in one request share the same state. Each answer is stored under the question name.

## Select a model

The default model is `MoritzLaurer/ModernBERT-large-zeroshot-v2.0`.

Set `OPENDECISION_MODEL` before starting the API to use another compatible zero-shot or NLI model:

```bash
OPENDECISION_MODEL=tasksource/ModernBERT-large-nli \
opendecision serve
```

The optional `model` field in a `/v1/systemone` request exists for TypeSafe SDK compatibility. The server uses the model selected at startup.

## TypeSafe SDK client

Install the optional client dependency to run the TypeSafe SDK example:

```bash
pip install "OpenDecision[typesafe]"
```

Or:

```bash
uv add "OpenDecision[typesafe]"
```

## Run offline after the model is cached

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run python your_script.py
```

## Run tests

Clone the repository and install the development environment:

```bash
git clone https://github.com/deepanwadhwa/OpenDecision.git
cd OpenDecision
uv sync --python 3.13 --all-groups
```

```bash
uv run --python 3.13 pytest -v
```

The model-backed tests load the configured model and can take longer than ordinary unit tests.
