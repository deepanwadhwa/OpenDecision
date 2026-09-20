from __future__ import annotations

import argparse
import json
from pathlib import Path

from opendecision.engine import OpenDecisionEngine

from questions import CHOICE_QUESTIONS, NOUL_QUESTIONS, SCORE_QUESTIONS


DEFAULT_DOCUMENT = Path("tests/GDPR_wiki_test.txt")
DEFAULT_MODEL = "tasksource/ModernBERT-large-nli"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    document = args.document.read_text(encoding="utf-8")
    engine = OpenDecisionEngine(model=args.model)
    rows = []

    for question_id, question in NOUL_QUESTIONS.items():
        result = engine.noul(
            state=document,
            instructions=question["instructions"],
        )
        probability = result["noul"]
        predicted = probability >= 0.5
        rows.append(
            {
                "id": question_id,
                "type": "noul",
                "expected": question["expected"],
                "predicted": predicted,
                "correct": predicted == question["expected"],
                "metric": probability,
            }
        )

    for question_id, question in CHOICE_QUESTIONS.items():
        result = engine.choice(
            state=document,
            instructions=question["instructions"],
            criteria=question["criteria"],
        )
        rows.append(
            {
                "id": question_id,
                "type": "choice",
                "expected": question["expected"],
                "predicted": result["choice"],
                "correct": result["choice"] == question["expected"],
                "metric": max(result["probabilities"].values()),
                "probabilities": result["probabilities"],
            }
        )

    for question_id, question in SCORE_QUESTIONS.items():
        result = engine.score(
            state=document,
            instructions=question["instructions"],
            criteria=question["criteria"],
        )
        maximum = len(question["criteria"]) - 1
        predicted_index = round(result["score"])
        rows.append(
            {
                "id": question_id,
                "type": "score",
                "expected": question["expected_index"],
                "predicted": predicted_index,
                "correct": predicted_index == question["expected_index"],
                "score": result["score"],
                "metric": result["score"] / maximum,
                "probabilities": result["probabilities"],
            }
        )

    binary_rows = [
        row for row in rows if row["type"] in {"noul", "choice"}
    ]
    correct = sum(row["correct"] for row in binary_rows)
    payload = {
        "document": str(args.document),
        "model": args.model,
        "characters": len(document),
        "summary": {
            "objective_correct": correct,
            "objective_total": len(binary_rows),
            "objective_accuracy": correct / len(binary_rows),
            "score_questions": len(rows) - len(binary_rows),
        },
        "results": rows,
    }

    for row in rows:
        if row["type"] in {"noul", "choice"}:
            marker = "PASS" if row["correct"] else "FAIL"
            print(
                f"{marker:<4} {row['id']:<24} {row['type']:<7} "
                f"expected={str(row['expected']):<16} "
                f"predicted={str(row['predicted']):<16} "
                f"metric={row['metric']:.3f}"
            )
        else:
            print(
                f"INFO {row['id']:<24} score   "
                f"raw={row['score']:.3f} normalized={row['metric']:.3f}"
            )

    print(
        f"\nWhole-document Noul/Choice accuracy: "
        f"{correct}/{len(binary_rows)} = {correct / len(binary_rows):.1%}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
