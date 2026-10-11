"""Optional image decisions. No image libraries or weights load on text requests."""
from __future__ import annotations

import base64
import binascii
from io import BytesIO
from typing import Any, Mapping, Sequence
import warnings

import torch

from opendecision.engine import _best_device, _distribution_confidence

DEFAULT_IMAGE_MODEL = "google/siglip2-base-patch16-224"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


def decode_image(data: str):
    """Decode bounded base64 image bytes; never fetch URLs or server files."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if len(data) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
        raise ValueError("Image exceeds the 10 MiB encoded-file limit.")
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Image data must be valid base64.") from error
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must contain between 1 byte and 10 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Image must be JPEG, PNG, or WebP.")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image exceeds the 20 megapixel limit.")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Animated images are not supported.")
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValueError("Invalid or oversized image.") from error


class ImageDecisionEngine:
    """SigLIP image/text matching with the same typed answer shapes as text.

    Scores measure visual matches, not entailment or calibrated truth.
    Inject model/processor together for offline testing or custom loading.
    """

    def __init__(self, model: str = DEFAULT_IMAGE_MODEL, device=None,
                 *, model_instance=None, processor=None):
        if (model_instance is None) != (processor is None):
            raise ValueError("Provide both model_instance and processor.")
        if model_instance is None:
            from transformers import AutoModel, AutoProcessor

            device = _best_device() if device is None else device
            device = "cpu" if device == -1 else device
            device = f"cuda:{device}" if isinstance(device, int) else device
            processor = AutoProcessor.from_pretrained(model)
            model_instance = AutoModel.from_pretrained(model).to(device).eval()
        self.model = model_instance
        self.processor = processor
        self.model_name = model

    def _logits(self, state: Any, descriptions: Sequence[str]) -> torch.Tensor:
        inputs = self.processor(
            images=state, text=list(descriptions), return_tensors="pt",
            padding="max_length", max_length=64, truncation=True,
        ).to(self.model.device)
        with torch.inference_mode():
            return self.model(**inputs).logits_per_image[0].float().cpu()

    def _probabilities(self, state, descriptions):
        return torch.softmax(self._logits(state, descriptions), dim=0).tolist()

    def choice(self, *, state, instructions: str,
               criteria: Mapping[str, str | None]) -> dict:
        if len(criteria) < 2:
            raise ValueError("Choice requires at least two candidates.")
        descriptions = [description or name.replace("_", " ")
                        for name, description in criteria.items()]
        probabilities = dict(zip(criteria, self._probabilities(state, descriptions)))
        return {"type": "choice", "choice": max(probabilities, key=probabilities.get),
                "probabilities": probabilities,
                "confidence": _distribution_confidence(probabilities)}

    def noul(self, *, state, instructions: str,
             criteria: Mapping[str, str] | None = None) -> dict:
        if criteria is None:
            probability = torch.sigmoid(self._logits(state, [instructions]))[0].item()
        else:
            probability = self._probabilities(state, [criteria["true"], criteria["false"]])[0]
        return {"type": "noul", "noul": probability}

    def score(self, *, state, instructions: str, criteria: Sequence[str]) -> dict:
        if len(criteria) < 2 or len(set(criteria)) != len(criteria):
            raise ValueError("Score requires at least two unique levels.")
        probabilities = dict(zip(map(str, range(len(criteria))),
                                 self._probabilities(state, criteria)))
        return {"type": "score",
                "score": sum(int(i) * p for i, p in probabilities.items()),
                "legend": dict(zip(map(str, range(len(criteria))), criteria)),
                "probabilities": probabilities,
                "confidence": _distribution_confidence(probabilities)}

    def relation(self, *, state, proposition: str, contradiction: str,
                 threshold: float = 0.5) -> dict:
        if not 0 < threshold < 1:
            raise ValueError("threshold must be between 0 and 1.")
        support, contradict = torch.sigmoid(
            self._logits(state, [proposition, contradiction])).tolist()
        if support >= threshold and contradict >= threshold:
            relation = "conflicted"
        elif support >= threshold:
            relation = "supports"
        elif contradict >= threshold:
            relation = "contradicts"
        else:
            relation = "unknown"
        return {"type": "relation", "relation": relation,
                "scores": {"supports": support, "contradicts": contradict},
                "threshold": threshold, "backend": "siglip_image_text"}

    def estimate_input_tokens(self, payload: dict) -> int:
        """Logical text tokens only; image bytes are not text tokens."""
        import json

        text = json.dumps({**payload, "state": {"type": "image"}},
                          ensure_ascii=False, sort_keys=True)
        return len(self.processor.tokenizer(text, add_special_tokens=False)["input_ids"])
