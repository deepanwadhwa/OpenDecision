# OpenDecision

[![Tests](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml/badge.svg)](https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Backend](https://img.shields.io/badge/backend-ModernBERT--large--zeroshot-6f42c1)

**OpenDecision is an open-source semantic decision engine.**

Give it some state, a natural-language question, and answer criteria. It returns a structured decision rather than generating free-form text.

## Why I built this

A few days ago, I saw TypeSafe announce [Jev, their first "System One Model"](https://typesafe.ai/blog/introducing-system-one-models-and-jev). While it looked impressive, it also kind of tingled my spidey sense.

A couple of years ago, I had worked on something similar for a client, using zero-shot models in a narrow domain involving healthcare insurance fraud. I also have experience training and building things with zero-shot models through projects like [Zink](https://github.com/deepanwadhwa/zink), so I thought I'd give this a try: build an open-source package that could leverage zero-shot models to provide a similar kind of functionality to what TypeSafe's Jev does.

That experiment became OpenDecision.

OpenDecision currently provides three primitives:

- **Choice** — select one answer from a supplied set.
- **Noul** — evaluate a binary natural-language predicate.
- **Score** — score state against an ordered natural-language rubric.

The default backend is [`MoritzLaurer/ModernBERT-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0), a compact zero-shot NLI model.

## Why?

Many application decisions do not require a generative LLM.

Examples:

- route a support request,
- choose a tool or function,
- classify a document,
- apply a semantic policy,
- match an entity,
- detect whether a condition is true,
- score severity against a rubric.

OpenDecision turns those problems into small, typed semantic decisions.

## Install and run

Python 3.13 is recommended.

```bash
git clone https://github.com/deepanwadhwa/OpenDecision.git
cd OpenDecision

uv sync --python 3.13 --all-groups
```

Start the API:

```bash
uv run uvicorn opendecision.api.app:app \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000
```

Then open:

```text
http://127.0.0.1:8000/docs
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

The model is downloaded from Hugging Face on first use.

## Python quickstart

```python
from opendecision.engine import OpenDecisionEngine

engine = OpenDecisionEngine()

result = engine.choice(
    state="The customer says the router has no power and the ISP line is working.",
    instructions="Who should handle this issue?",
    criteria={
        "isp": "The internet service provider should investigate the connection.",
        "router_manufacturer": "The router or its power hardware should be investigated.",
        "electric_utility": "The electricity provider should investigate an outage.",
    },
)

print(result["choice"])
print(result["probabilities"])
print(result["confidence"])
```

A `Choice` response has the form:

```python
{
    "type": "choice",
    "choice": "router_manufacturer",
    "probabilities": {
        "isp": ...,
        "router_manufacturer": ...,
        "electric_utility": ...,
    },
    "confidence": ...,
}
```

`confidence` is a normalized measure of concentration in the returned probability distribution. It is **not** a calibrated probability that the answer is correct.

### Noul

```python
result = engine.noul(
    state="The request says the production service is currently unavailable.",
    instructions="This request is time-sensitive.",
)

print(result["noul"])
```

### Score

```python
result = engine.score(
    state="The application crashes for every user at startup.",
    instructions="How severe is this software bug?",
    criteria={
        "0": "Cosmetic or negligible impact.",
        "1": "Minor impact with an easy workaround.",
        "2": "Significant impact, but the core workflow remains usable.",
        "3": "Major failure blocking an important workflow.",
        "4": "Critical failure preventing normal use.",
    },
)

print(result["score"])
```

## Choice architecture

OpenDecision does not rely on one fixed textual formulation for `Choice`.

The current v0.1 strategy evaluates the request with two complementary semantic compilers:

**Compiler A**

```text
premise:    state
candidates: answer descriptions
hypothesis: question-conditioned
```

**Compiler B**

```text
premise:    state
candidates: label + description
hypothesis: default NLI hypothesis
```

If A and B agree, their answer is returned.

If they disagree, OpenDecision runs a small semantic adjudication over the two competing answers:

```text
premise:    state + question
candidates: labels only
hypothesis: default NLI hypothesis
```

This uses the same underlying ModernBERT model throughout; no additional router model is required.

## Evaluation

### OpenDecision Original Choice 500

The project includes an original synthetic benchmark containing **500 Choice cases across 25 domains**:

- 375 development cases
- 125 held-out comparison cases

The benchmark covers support routing, function routing, citation relations, semantic extraction, date semantics, product taxonomy, entity matching, policy decisions, software bugs, document types, logistics, security events, scientific methods, word sense, and more.

### Results

Backend: `MoritzLaurer/ModernBERT-large-zeroshot-v2.0`

| Method | Dev (375) | Holdout (125) |
|---|---:|---:|
| Single best universal compiler | 304/375 — **81.1%** | 102/125 — **81.6%** |
| A + B + semantic adjudicator | 321/375 — **85.6%** | 108/125 — **86.4%** |
| Per-case A/B oracle upper bound | 340/375 — **90.7%** | 113/125 — **90.4%** |

On the holdout split:

- A and B agreed on **96/125 (76.8%)** requests.
- The adjudicator was invoked on **29/125 (23.2%)** requests.
- It selected the correct answer on **21/29 (72.4%)** disagreements.
- Final accuracy was **108/125 (86.4%)**.

The oracle row is **not a deployable system result**. It only measures the maximum possible accuracy if a perfect selector always knew whether Compiler A or Compiler B was correct.

### Evaluation caveat

This is an **internal synthetic benchmark**, not an external standardized benchmark. The final adjudicator profile was selected on the 375-case development split and then evaluated on the 125-case split. The holdout split had also been inspected during earlier compiler-comparison experiments, so the 86.4% result should be treated as an internal held-out comparison rather than a pristine external test result.

The benchmark and split manifest are included in the repository so results can be reproduced.

## TypeSafe SDK compatibility

OpenDecision exposes a `/v1/systemone` endpoint compatible with the core request/response flow used by the TypeSafe SDK.

A local OpenDecision server can therefore be used as a `base_url` for compatible clients.

## API

Once the server is running:

```text
GET  /health
POST /v1/systemone
GET  /docs
GET  /openapi.json
```

FastAPI's interactive documentation at `/docs` is the easiest way to inspect the exact request schema and try requests manually.

## Run the evaluations

General benchmark runner:

```bash
uv run python benchmarks/run_eval.py \
  --cases benchmarks/cases.jsonl
```

Original benchmark:

```bash
uv run python benchmarks/run_eval.py \
  --cases benchmarks/opendecision_original/dev.jsonl
```

The experimental compiler/adjudicator scripts live under `benchmarks/`.

## Run tests

```bash
uv run --python 3.13 pytest -v
```

CI runs the same test suite on GitHub Actions.

## Design principles

OpenDecision is intentionally small:

- structured outputs instead of token generation,
- explicit answer criteria,
- local/open model backend,
- typed decision primitives,
- reproducible compiler formulations,
- inspectable probabilities,
- no hosted service dependency.

## Current limitations

- The default probabilities are NLI scores and should not be assumed calibrated.
- Some tasks involving exact dates, symbolic reasoning, close citation relations, or subtle policies remain difficult for the current ~400M backend.
- The original benchmark is synthetic and should be supplemented with external task-specific evaluations before making strong general-performance claims.
- The adjudicated `Choice` path may require three classifier passes when the two primary compilers disagree.

## Project status

**v0.1.0** is intended as a developer preview.

The core primitives, local API, SDK-compatible endpoint, evaluation harness, and reproducible benchmark are available for experimentation.
