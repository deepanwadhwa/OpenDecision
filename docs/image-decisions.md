# Image decisions

Install the optional image dependencies:

```bash
pip install 'OpenDecision[images]'
# From the repository:
uv sync --extra images --all-groups
```

Image decisions use `google/siglip2-base-patch16-224`. The API loads it once,
when the first valid image request arrives. Text and document requests keep
using the configured text model. The first image request downloads the model
from Hugging Face and can take longer than subsequent requests.

## Same endpoint and question shapes

Send `POST /v1/systemone` with an explicit image state:

```json
{
  "model": "google/siglip2-base-patch16-224",
  "state": {"type": "image", "data": "BASE64_IMAGE_BYTES"},
  "questions": {
    "scene": {
      "type": "choice",
      "instructions": "Which scene is visible?",
      "criteria": {
        "indoors": "An indoor room",
        "outdoors": "An outdoor landscape"
      }
    },
    "animal": {
      "type": "noul",
      "instructions": "A dog is visible in the image."
    },
    "brightness": {
      "type": "score",
      "instructions": "How bright is the scene?",
      "criteria": ["A dark scene", "A moderately lit scene", "A brightly lit scene"]
    },
    "dog_evidence": {
      "type": "relation",
      "proposition": "A dog is visible in the image.",
      "contradiction": "An empty scene without any animals.",
      "threshold": 0.5
    }
  }
}
```

`model` is optional for image states. If supplied, it must be the SigLIP2 model
above. Answers keep the existing `choice`, `noul`, `score`, and `relation`
structures; the response identifies the actual image model. Usage counts
logical text input tokens and reports zero output tokens. Image bytes and vision compute are excluded from the token count.

Run the included example against a local server:

```bash
opendecision serve
uv run --extra images python examples/image_decisions.py /path/to/image.jpg
```

Images must be single-frame JPEG, PNG, or WebP, at most 10 MiB and 20 megapixels.
`data` contains plain base64 file bytes, without a data-URL prefix. The server
does not fetch image URLs or read file paths from requests. EXIF orientation is
applied before RGB conversion. Invalid inputs return 422; unavailable image
libraries or model files return 503.

## Python API

```python
from PIL import Image, ImageOps
from opendecision import ImageDecisionEngine

engine = ImageDecisionEngine()
with Image.open("photo.jpg") as source:
    image = ImageOps.exif_transpose(source).convert("RGB")

result = engine.choice(
    state=image,
    instructions="What is visible?",
    criteria={"dog": "A photo of a dog", "cat": "A photo of a cat"},
)
print(result)
```

The Python engine accepts a decoded PIL image. `decode_image` in
`opendecision.images` provides the same bounded base64 decoder as the API.

## Meaning of the scores

SigLIP2 scores image and text matches. Describe visible candidate answers as complete captions.
For image `choice` and `score`, the model matches the candidate descriptions
(or choice names when descriptions are absent) directly. `instructions` stays
in the API contract but does not condition those scores. For `noul` without
criteria, write the instruction as a visual statement.

- `Choice` uses softmax over image/text logits for a relative distribution.
- `Score` uses the same distribution and returns the expected zero-based level.
- `Noul` without criteria uses the independent sigmoid match score. With explicit
  true/false descriptions, it uses a relative softmax over those two descriptions.
- `Relation` independently scores the supplied proposition and contradiction
  with sigmoid, then applies the threshold to produce the four existing states.
  Its `backend` is `siglip_image_text`. These states describe visual matches. Negation and absence descriptions can be unreliable.

Scores and entropy confidence are uncalibrated. A relative winner can be returned
when none of the descriptions fits. OCR, precise counting, and complex visual reasoning require separate evaluation. Test descriptions and thresholds on your
images before relying on decisions.

The processor uses the checkpoint's preprocessing with 64-token text padding and
truncation. Keep captions short. See the [model card](https://huggingface.co/google/siglip2-base-patch16-224)
and [Transformers documentation](https://huggingface.co/docs/transformers/model_doc/siglip2).

## Combining answers

[See image examples and returned decisions](image-examples.md).

The [image demo](https://github.com/deepanwadhwa/OpenDecision/tree/main/demos/images) runs editable questions against local
image files through the same API and composes an animal-present Noul with a
bear Choice using the existing rule evaluator. It returns a simulated alarm
action and the facts used to reach it. Application thresholds and actions remain
outside the model engine.

## API call times

The examples show measured HTTP call times on an Apple M3 using MPS acceleration.
Both models were loaded before timing. Each request had one warmup call, followed
by five measured calls. The displayed time is the median.

The timer starts before the HTTP client sends the JSON request and stops after
the response is parsed. It includes request serialization, transfer over localhost,
image decoding, model inference, and response parsing. Image file reading, base64
encoding, model downloads, and model loading happen before the timer starts.

Homepage times cover the questions displayed there. Gallery times cover all
questions shown for each photo. The fence gallery includes an additional material
question. Times vary with the device, image size, and question count.

Reproduce the measurements from the repository:

```bash
uv run --extra images python demos/images/measure_latency.py /path/to/images
```

The script starts a local HTTP server, sends the requests, saves every measured
time and response to `build/image-evaluation/api-timings.json`, and stops the server.
