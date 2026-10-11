import base64
from io import BytesIO
from types import SimpleNamespace

import pytest
import torch
from fastapi.testclient import TestClient
Image = pytest.importorskip("PIL.Image", reason="Install the images extra to test image decoding.")

from opendecision.api.app import app
from opendecision.images import ImageDecisionEngine, decode_image


class Inputs(dict):
    def to(self, device):
        return self


class Processor:
    def __init__(self):
        self.calls = []
        self.tokenizer = lambda *a, **k: {"input_ids": [1, 2, 3]}

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return Inputs()


@pytest.fixture
def engine():
    processor = Processor()

    class Model:
        device = "cpu"

        def __call__(self, **kwargs):
            count = len(processor.calls[-1]["text"])
            return SimpleNamespace(logits_per_image=torch.tensor([[2., -2., 0.][:count]]))

    return ImageDecisionEngine(model_instance=Model(), processor=processor)


def encoded_image():
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_decode_and_validation():
    assert decode_image(encoded_image()).mode == "RGB"
    for data in ["", "not base64", base64.b64encode(b"not an image").decode()]:
        with pytest.raises(ValueError):
            decode_image(data)


def test_decoder_bounds_and_formats(monkeypatch):
    import opendecision.images as images

    monkeypatch.setattr(images, "MAX_IMAGE_PIXELS", 2)
    with pytest.raises(ValueError, match="megapixel"):
        decode_image(encoded_image())
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 1)
    with pytest.raises(ValueError, match="limit"):
        decode_image(encoded_image())


def test_decoder_rejects_unsupported_and_animated_images():
    for image_format, options in [("GIF", {}), ("PNG", {"save_all": True,
                                  "append_images": [Image.new("RGB", (4, 4), "blue")]})]:
        buffer = BytesIO()
        Image.new("RGB", (4, 4), "red").save(buffer, format=image_format, **options)
        with pytest.raises(ValueError):
            decode_image(base64.b64encode(buffer.getvalue()).decode())


def test_all_primitives_and_preprocessing(engine):
    image = decode_image(encoded_image())
    choice = engine.choice(state=image, instructions="What is visible?",
                           criteria={"red": "A red image", "blue": "A blue image"})
    assert choice["choice"] == "red"
    assert sum(choice["probabilities"].values()) == pytest.approx(1)
    assert engine.noul(state=image, instructions="A red image")["noul"] == pytest.approx(torch.sigmoid(torch.tensor(2.)).item())
    assert engine.noul(state=image, instructions="Is it red?",
                       criteria={"true": "red", "false": "blue"})["noul"] > .9
    score = engine.score(state=image, instructions="How red?", criteria=["red", "blue"])
    assert 0 <= score["score"] <= 1
    assert score["legend"] == {"0": "red", "1": "blue"}
    relation = engine.relation(state=image, proposition="red", contradiction="blue")
    assert relation["relation"] == "supports"
    assert engine.relation(state=image, proposition="red", contradiction="blue", threshold=.95)["relation"] == "unknown"
    for call in engine.processor.calls:
        assert call["images"] is image
        assert call["padding"] == "max_length"
        assert call["max_length"] == 64
        assert call["truncation"] is True


@pytest.mark.parametrize("logits, expected", [([2., 2.], "conflicted"), ([-2., 2.], "contradicts"), ([-2., -2.], "unknown")])
def test_relation_states(engine, monkeypatch, logits, expected):
    monkeypatch.setattr(engine, "_logits", lambda *args: torch.tensor(logits))
    assert engine.relation(state=None, proposition="yes", contradiction="no")["relation"] == expected


def test_primitive_validation(engine):
    with pytest.raises(ValueError):
        engine.choice(state=None, instructions="", criteria={"a": None})
    with pytest.raises(ValueError):
        engine.score(state=None, instructions="", criteria=["a", "a"])
    with pytest.raises(ValueError):
        engine.relation(state=None, proposition="", contradiction="", threshold=1)


def test_image_api_and_rejections(engine, monkeypatch):
    import importlib
    api = importlib.import_module("opendecision.api.app")
    calls = []
    monkeypatch.setattr(api, "get_image_engine", lambda app: calls.append(True) or engine)
    # No lifespan: these tests must neither load nor download the text model.
    client = TestClient(app)
    payload = {"state": {"type": "image", "data": encoded_image()},
               "questions": {
                   "color": {"type": "choice", "instructions": "Which color?",
                             "criteria": {"red": "red", "blue": "blue"}},
                   "red": {"type": "noul", "instructions": "red"},
                   "scale": {"type": "score", "instructions": "Color?", "criteria": ["red", "blue"]},
                   "relation": {"type": "relation", "proposition": "red", "contradiction": "blue"}}}
    response = client.post("/v1/systemone", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == engine.model_name
    assert body["answers"]["color"]["choice"] == "red"
    assert body["usage"] == {"input_tokens": 3, "output_tokens": 0}
    assert len(calls) == 1
    payload["state"]["data"] = "bad!"
    assert client.post("/v1/systemone", json=payload).status_code == 422
    assert len(calls) == 1
    payload["state"]["data"] = encoded_image()
    payload["state"]["url"] = "http://localhost/private"
    assert client.post("/v1/systemone", json=payload).status_code == 422
    del payload["state"]["url"]
    payload["model"] = "text-model"
    assert client.post("/v1/systemone", json=payload).status_code == 422
    payload["model"] = engine.model_name
    payload["state"] = "text"
    assert client.post("/v1/systemone", json=payload).status_code == 422


def test_text_api_still_uses_text_engine(engine, monkeypatch):
    engine.classifier = SimpleNamespace(tokenizer=engine.processor.tokenizer)
    monkeypatch.setattr(app.state, "engine", engine, raising=False)
    monkeypatch.setattr(app.state, "model_name", "text-test", raising=False)
    response = TestClient(app).post("/v1/systemone", json={
        "state": "text", "questions": {"q": {"type": "choice", "instructions": "?",
                                               "criteria": {"a": "a", "b": "b"}}}})
    # Adapt the stub to the existing token usage interface.
    assert response.status_code == 200
    assert response.json()["model"] == "text-test"


def test_image_engine_loads_once(engine, monkeypatch):
    import importlib
    import opendecision.images as images

    api = importlib.import_module("opendecision.api.app")
    calls = []
    monkeypatch.setattr(app.state, "image_engine", None, raising=False)
    monkeypatch.setattr(images, "ImageDecisionEngine", lambda: calls.append(True) or engine)
    assert api.get_image_engine(app) is engine
    assert api.get_image_engine(app) is engine
    assert calls == [True]


def test_image_model_unavailable_returns_503(monkeypatch):
    import importlib

    api = importlib.import_module("opendecision.api.app")

    def unavailable(app):
        raise OSError("model unavailable")

    monkeypatch.setattr(api, "get_image_engine", unavailable)
    response = TestClient(app).post("/v1/systemone", json={
        "state": {"type": "image", "data": encoded_image()},
        "questions": {"q": {"type": "noul", "instructions": "A red image"}}})
    assert response.status_code == 503
