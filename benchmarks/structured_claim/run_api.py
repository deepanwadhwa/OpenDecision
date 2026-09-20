from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


HERE = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/v1/documents/decide",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    request = json.loads((HERE / "request.json").read_text())
    expected = json.loads((HERE / "expected.json").read_text())
    response = httpx.post(args.url, json=request, timeout=300.0)
    response.raise_for_status()
    payload = response.json()

    correct = 0
    determined = 0
    for question_id, expected_answer in expected.items():
        result = payload["answers"][question_id]
        actual = result["answer"]
        passed = actual == expected_answer
        determined += actual is not None
        correct += passed
        print(
            f"{'PASS' if passed else 'FAIL':<4} "
            f"{question_id:<18} expected={str(expected_answer):<5} "
            f"actual={str(actual):<5} status={result['status']:<10} "
            f"binary_true={result['binary']['probabilities']['true']:.3f} "
            f"relation={result['three_way']['relation']:<11} "
            f"unknown={result['three_way']['scores'].get('unknown', 0.0):.3f}"
        )

    total = len(expected)
    print(
        f"\nAccuracy: {correct}/{total} = {correct / total:.1%}; "
        f"determined: {determined}/{total}; chunks: {payload['chunks']}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
