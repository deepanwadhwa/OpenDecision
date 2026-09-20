from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from opendecision.rules import evaluate_rule, relation_status


HERE = Path(__file__).parent


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def deterministic_facts() -> dict[str, str]:
    collision = datetime.fromisoformat("2026-04-16T18:43:00")
    emergency_arrival = datetime.fromisoformat("2026-04-17T09:18:00")
    treatment_delay = emergency_arrival - collision

    return {
        "treatment_within_24_hours": (
            "established"
            if treatment_delay.total_seconds() <= 24 * 60 * 60
            else "refuted"
        ),
        # Pickup time is explicitly outstanding, so necessity of the final
        # rental day cannot be established or refuted from the current file.
        "rental_necessity_established": "unknown",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--facts-result",
        type=Path,
        default=Path(
            "benchmarks/results/insurance_claim_facts_tasksource_nli.json"
        ),
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=HERE / "decisions.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    fact_payload = load_json(args.facts_result)
    facts = {
        row["id"]: relation_status(row["predicted"])
        for row in fact_payload["results"]
    }
    facts.update(deterministic_facts())

    rows = []

    for decision in load_json(args.decisions):
        trace = evaluate_rule(decision["rule"], facts)
        predicted = trace["status"]
        rows.append(
            {
                "id": decision["id"],
                "expected": decision["expected"],
                "predicted": predicted,
                "correct": predicted == decision["expected"],
                "trace": trace,
            }
        )

    correct = sum(row["correct"] for row in rows)
    payload = {
        "summary": {
            "correct": correct,
            "total": len(rows),
            "accuracy": correct / len(rows),
        },
        "results": rows,
    }

    for row in rows:
        marker = "PASS" if row["correct"] else "FAIL"
        print(
            f"{marker:<4} {row['id']:<32} "
            f"expected={row['expected']:<11} "
            f"predicted={row['predicted']}"
        )

    print(f"\nComposed decisions: {correct}/{len(rows)} = {correct / len(rows):.1%}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
