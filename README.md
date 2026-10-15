<div align="center">

<h1>OpenDecision</h1>

<p>Typed decisions for text, documents, and images.</p>

<p>
  <a href="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/tests.yml/badge.svg"></a>
  <a href="https://pypi.org/project/OpenDecision/"><img alt="Version" src="https://img.shields.io/pypi/v/OpenDecision?label=version&color=2563eb"></a>
  <a href="https://pypi.org/project/OpenDecision/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/OpenDecision?color=2563eb"></a>
  <a href="https://github.com/deepanwadhwa/OpenDecision/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/OpenDecision?color=2563eb"></a>
  <a href="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/docs.yml"><img alt="Documentation" src="https://github.com/deepanwadhwa/OpenDecision/actions/workflows/docs.yml/badge.svg"></a>
</p>

<p>
  <a href="https://deepanwadhwa.github.io/OpenDecision/quickstart/#memory"><img alt="Text: 1.1 GB RAM measured on CPU" src="https://img.shields.io/badge/Text_RAM-1.1_GB_measured-2563eb"></a>
  <a href="https://deepanwadhwa.github.io/OpenDecision/quickstart/#memory"><img alt="Text and images: 2.1 GB RAM measured on CPU" src="https://img.shields.io/badge/Text_%2B_images_RAM-2.1_GB_measured-2563eb"></a>
  <a href="https://deepanwadhwa.github.io/OpenDecision/quickstart/#input-limits"><img alt="Text context: 512 to 8,192 tokens, depending on question type" src="https://img.shields.io/badge/Text_context-512%E2%80%938%2C192_tokens-2563eb"></a>
  <a href="https://deepanwadhwa.github.io/OpenDecision/quickstart/#input-limits"><img alt="Images processed at 224 by 224 pixels" src="https://img.shields.io/badge/Image_input-224_%C3%97_224_px-2563eb"></a>
</p>

<p>
  <a href="https://deepanwadhwa.github.io/OpenDecision/">Documentation</a> ·
  <a href="#image-examples">Image examples</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="#api-surface">API</a> ·
  <a href="https://deepanwadhwa.github.io/OpenDecision/examples/">Examples</a>
</p>

</div>

Send text, JSON, a document, or an image with typed questions. OpenDecision runs locally and returns structured answers.

With the default models, Choice, Score, and Relation use up to **512 tokens** per text evaluation; yes/no (`Noul`) uses up to **8,192 tokens**. Tokens are pieces of words, and these limits include the question text sent to the model. Images are resized to **224 × 224 pixels**, with up to **64 tokens per caption**. The document API splits longer documents into passages. [Input limits](https://deepanwadhwa.github.io/OpenDecision/quickstart/#input-limits).

OpenDecision provides:

- `Choice` to select one option from a list.
- `Noul` to score a statement or compare explicit true/false descriptions.
- `Score` to place state on an ordered scale.
- `Relation` to report `supports`, `contradicts`, `unknown`, or `conflicted`.
- Document processing with evidence retrieval and source passages.
- Image decisions with optional SigLIP2 support and the same typed questions.
- A Python API, a FastAPI server, and a TypeSafe SDK compatible endpoint.

The default backend is [`MoritzLaurer/ModernBERT-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0). [`MoritzLaurer/deberta-v3-large-zeroshot-v2.0`](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0) is an optional model. Image decisions use [`google/siglip2-base-patch16-224`](https://huggingface.co/google/siglip2-base-patch16-224). See [model selection and evaluation](https://deepanwadhwa.github.io/OpenDecision/model-selection/) for the measured tradeoffs.

OpenDecision is licensed under Apache 2.0.

## Image examples

### Wildlife alert

<img src="https://raw.githubusercontent.com/deepanwadhwa/OpenDecision/main/docs/assets/images/bear.jpg" alt="A bear in a wooded landscape" width="360">

| Question | Answer |
| --- | --- |
| Is an animal visible? | Yes |
| What kind of animal is visible? | `bear` |

Animal present and type `bear` returns **`sound_alarm`**.

**API call: 318 ms** for both questions.

### Bin collection

<img src="https://raw.githubusercontent.com/deepanwadhwa/OpenDecision/main/docs/assets/images/overflowing-bin.jpg" alt="An overflowing bin with litter on the floor" width="360">

| Question | Answer |
| --- | --- |
| Is a bin visible? | Yes |
| What condition is the bin in? | `overflowing` |
| Is litter scattered on the floor? | Yes |

Bin present and condition `overflowing` returns **`request_collection`**.

**API call: 234 ms** for all three questions.

### Fence repair

<img src="https://raw.githubusercontent.com/deepanwadhwa/OpenDecision/main/docs/assets/images/damaged-fence.jpg" alt="A damaged metal fence leaning into vegetation" width="360">

| Question | Answer |
| --- | --- |
| Is a fence visible? | Yes |
| What condition is the fence in? | `damaged` |

Fence present and condition `damaged` returns **`create_repair_task`**.

**API call: 155 ms** for both questions.

These are recorded SigLIP2 results. The actions are simulated. Call times are medians of five local HTTP requests on an Apple M3 with the models loaded. The rules use a yes/no threshold of 0.5 and require a winning Choice probability of at least 0.6.

[More images and answers](https://deepanwadhwa.github.io/OpenDecision/image-examples/) · [Image API and setup](https://deepanwadhwa.github.io/OpenDecision/image-decisions/) · [Run the demo](https://github.com/deepanwadhwa/OpenDecision/tree/main/demos/images)

## Text and document examples

### Customer routing

> I was charged twice and I need this fixed before my meeting this afternoon.

| Question | Answer |
| --- | --- |
| Which department should handle this? | `billing` |
| Is this request urgent? | Yes |

**API call: 231 ms** for both questions, measured with the same method as the image examples.

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

The saved synthetic claim benchmark retrieves 17 required facts and matches 10 composed decisions. See the [insurance claim benchmark](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/insurance_claim/README.md).

#### GDPR example

The GDPR example uses a 54,171-character document split into 31 sections.

| Question | Answer |
| --- | --- |
| Must a personal data breach be reported within 72 hours? | `true` |
| Must every organization appoint a Data Protection Officer? | `false` |
| Can pre-ticked boxes count as valid consent? | `false` |
| What is the maximum fine for serious infringements? | `EUR 20 million or 4% of worldwide turnover` |

The saved retrieval benchmark answers 9 of 10 questions correctly. See the [questions](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/gdpr_wiki/questions.py) and [saved results](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/gdpr_wiki_retrieved.json).

#### Yes/no answer modes

`POST /v1/documents/decide` has one `noul_mode` setting:

| Mode | Result |
| --- | --- |
| `binary` | Always chooses `true` or `false`. |
| `three_way` | Returns `supports`, `contradicts`, or `unknown`. |
| `both` | Runs both evaluations. This is the default. |

In `both` mode, OpenDecision reports `confirmed`, `tentative`, or `conflicted`. A conflict has `answer: null`. Both score distributions remain in the response.

The `noul_mode` setting applies to document `Noul` questions.

## Get started

OpenDecision requires Python 3.13 or later.

In a CPU check with the default models, the app used about **1.1 GB of RAM for text**, **1.4 GB for images alone**, or **2.1 GB with both models loaded**. The API keeps both models loaded after the first image request. These are measured examples, not minimum requirements; longer inputs and simultaneous requests can use more memory. Leave room for your operating system and other apps. [Memory measurement details](https://deepanwadhwa.github.io/OpenDecision/quickstart/#memory).

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

For image support:

```bash
pip install 'OpenDecision[images]'
```

```python
from PIL import Image, ImageOps
from opendecision import ImageDecisionEngine

engine = ImageDecisionEngine()
with Image.open("photo.jpg") as source:
    image = ImageOps.exif_transpose(source).convert("RGB")

result = engine.choice(
    state=image,
    instructions="What kind of animal is visible?",
    criteria={"cat": "A photo of a cat", "bear": "A photo of a bear"},
)
print(result["choice"])
```

The API accepts the same question types with an image state:

```json
{
  "state": {"type": "image", "data": "BASE64_IMAGE_BYTES"},
  "questions": {
    "animal_type": {
      "type": "choice",
      "instructions": "What kind of animal is visible?",
      "criteria": {"cat": "A photo of a cat", "bear": "A photo of a bear"}
    }
  }
}
```

Images must be single-frame JPEG, PNG, or WebP, up to 10 MiB and 20 megapixels. The server loads SigLIP2 on the first valid image request.

## Documentation

- [Documentation index](https://deepanwadhwa.github.io/OpenDecision/)
- [Quick start and API](https://deepanwadhwa.github.io/OpenDecision/quickstart/)
- [Choice, Noul, Score, and Relation](https://deepanwadhwa.github.io/OpenDecision/primitives/)
- [Documents, evidence, and yes/no modes](https://deepanwadhwa.github.io/OpenDecision/document-decisions/)
- [Image examples](https://deepanwadhwa.github.io/OpenDecision/image-examples/)
- [Image decisions and SigLIP2](https://deepanwadhwa.github.io/OpenDecision/image-decisions/)
- [Evidence relations and rules](https://deepanwadhwa.github.io/OpenDecision/evidence-and-rules/)
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

OpenDecision v0.2.0 is a developer preview.

Model scores are uncalibrated. Test captions and thresholds on your own images and documents. Counting and negated image captions produced errors in the sample tests.
