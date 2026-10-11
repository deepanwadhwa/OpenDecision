"""Submit a local image to the existing decision API."""
import argparse
import base64
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    payload = {
        "state": {"type": "image", "data": base64.b64encode(args.image.read_bytes()).decode("ascii")},
        "questions": {
            "scene": {"type": "choice", "instructions": "Which scene is visible?",
                      "criteria": {"indoors": "An indoor room", "outdoors": "An outdoor landscape"}},
            "animal": {"type": "noul", "instructions": "An animal is visible in the image."},
            "brightness": {"type": "score", "instructions": "How bright is the scene?",
                           "criteria": ["A dark scene", "A moderately lit scene", "A brightly lit scene"]},
        },
    }
    response = httpx.post(f"{args.base_url.rstrip('/')}/v1/systemone", json=payload, timeout=600)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
