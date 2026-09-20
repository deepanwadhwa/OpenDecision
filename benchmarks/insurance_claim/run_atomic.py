from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from opendecision.engine import DEFAULT_MODEL, OpenDecisionEngine


DEFAULT_CASES = Path(__file__).with_name("fact_cases.jsonl")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                cases.append(json.loads(line))

    return cases


def evaluate(
    engine: OpenDecisionEngine,
    cases: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    results = engine.relations(
        items=[
            {
                "state": case["evidence"],
                "proposition": case["proposition"],
                "contradiction": case["contradiction"],
            }
            for case in cases
        ],
        threshold=threshold,
    )

    rows = []

    for case, result in zip(cases, results):
        predicted = result["relation"]
        expected = case["expected"]
        rows.append(
            {
                "id": case["id"],
                "expected": expected,
                "predicted": predicted,
                "correct": predicted == expected,
                "scores": result["scores"],
                "source_ids": case["source_ids"],
            }
        )

    correct = sum(row["correct"] for row in rows)

    return {
        "summary": {
            "correct": correct,
            "total": len(rows),
            "accuracy": correct / len(rows) if rows else 0.0,
            "threshold": threshold,
        },
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = evaluate(
        OpenDecisionEngine(model=args.model),
        load_cases(args.cases),
        args.threshold,
    )

    for row in payload["results"]:
        marker = "PASS" if row["correct"] else "FAIL"
        support = row["scores"]["supports"]
        contradict = row["scores"]["contradicts"]
        print(
            f"{marker:<4} {row['id']:<32} "
            f"expected={row['expected']:<11} "
            f"predicted={row['predicted']:<11} "
            f"support={support:.3f} contradict={contradict:.3f}"
        )

    summary = payload["summary"]
    print(
        f"\nAtomic evidence relation: "
        f"{summary['correct']}/{summary['total']} "
        f"= {summary['accuracy']:.1%}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
