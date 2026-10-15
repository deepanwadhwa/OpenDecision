# Quick start and API

## Requirements

- Python 3.13 or later
- `pip` or `uv`
- RAM for the models, plus your operating system and other apps (see below)

### Memory

| What you run | Measured app RAM on CPU |
| --- | ---: |
| Text | About 1.1 GB |
| Images alone, using `ImageDecisionEngine` in Python | About 1.4 GB |
| Text and images, including the API after its first image request | About 2.1 GB |

These are measured examples, not minimum requirements. Leave room for your operating system and other apps. Longer text, larger batches, and simultaneous requests can use more memory. GPU memory use can differ.

Measured on October 15, 2026, on an Apple M3 using CPU inference, Python 3.13, PyTorch 2.14.0, and Transformers 5.17.0. Each row used a fresh Python process with the default model(s), measured from process startup through one two-option `choice()` call per model. Text used a short customer billing request; images used a 640 × 480 RGB image. Figures are peak process memory, rounded to decimal GB, including model loading and Python dependencies. They exclude other processes and GPU memory. Long document workloads and the optional DeBERTa model were not measured.

The default text model is `MoritzLaurer/ModernBERT-large-zeroshot-v2.0`; the image model is `google/siglip2-base-patch16-224`. The API loads the text model at startup and keeps the image model loaded after the first valid image request. A GPU is optional.

### Input limits

Tokens are pieces of words. Text limits include the input, the question or candidate description sent to the model, and special tokens.

| Input with the default models | Limit per evaluation |
| --- | --- |
| Text: Choice, Score, and Relation | 512 tokens |
| Text: yes/no (`Noul`) | 8,192 tokens |
| Documents | Split into passages of up to 384 tokens by default, then relevant passages are selected for each question |
| Images | Resized to 224 × 224 pixels for processing |
| Image captions or candidate descriptions | 64 tokens each, including special tokens |
| Image uploads through the API | Single-frame JPEG, PNG, or WebP; up to 10 MiB and 20 megapixels |

ModernBERT supports 8,192 tokens, but the current Choice, Score, and Relation paths use its tokenizer's 512-token limit. The `Noul` path explicitly uses the model's 8,192-token limit. Text beyond the applicable limit is truncated. Document passages are evaluated within these same limits; the whole document is not read in one pass. The optional DeBERTa model has a 512-token limit for all text question types.

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

To try DeBERTa in Python, select it explicitly:

```python
engine = OpenDecisionEngine(
    model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0"
)
```

Set `OPENDECISION_MODEL` before starting the API to use another compatible zero-shot or NLI model:

```bash
OPENDECISION_MODEL=MoritzLaurer/deberta-v3-large-zeroshot-v2.0 \
opendecision serve
```

You can also pass `opendecision serve --model MoritzLaurer/deberta-v3-large-zeroshot-v2.0`. See [model selection and evaluation](model-selection.md) before changing the default for an application.

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
