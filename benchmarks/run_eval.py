from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def default_output_path(cases_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = cases_path.parent.name or cases_path.stem
    return Path("benchmarks/results") / f"{name}_{stamp}.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("benchmarks/cases.jsonl"),
        help="JSONL benchmark file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to save JSON results. Defaults to benchmarks/results/<set>_<timestamp>.json",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    output_path = args.output or default_output_path(args.cases)

    engine = OpenDecisionEngine()

    choice_total = choice_correct = 0
    noul_total = noul_correct = 0
    score_errors: list[float] = []

    case_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for i, case in enumerate(cases, start=1):
        print(
            f"\r[{i}/{len(cases)}] {case['id']}",
            end="",
            flush=True,
        )
        case_type = case["type"]

        if case_type == "choice":
            raw = engine.choice(
                state=case["state"],
                instructions=case["instructions"],
                criteria=case["criteria"],
            )
            predicted = raw["choice"]
            expected = case["expected"]
            correct = predicted == expected

            choice_total += 1
            choice_correct += int(correct)

            record = {
                "id": case["id"],
                "type": "choice",
                "expected": expected,
                "predicted": predicted,
                "correct": correct,
                "probabilities": raw["probabilities"],
                "confidence": raw.get("confidence"),
            }

            if not correct:
                failures.append(record)

        elif case_type == "noul":
            raw = engine.noul(
                state=case["state"],
                instructions=case["instructions"],
                criteria=case.get("criteria"),
            )
            p_true = float(raw["noul"])
            predicted = p_true >= 0.5
            expected = bool(case["expected"])
            correct = predicted == expected

            noul_total += 1
            noul_correct += int(correct)

            record = {
                "id": case["id"],
                "type": "noul",
                "expected": expected,
                "predicted": predicted,
                "correct": correct,
                "p_true": p_true,
            }

            if not correct:
                failures.append(record)

        elif case_type == "score":
            raw = engine.score(
                state=case["state"],
                instructions=case["instructions"],
                criteria=case["criteria"],
            )
            predicted = float(raw["score"])
            expected = float(case["expected"])
            abs_error = abs(predicted - expected)
            score_errors.append(abs_error)

            record = {
                "id": case["id"],
                "type": "score",
                "expected": expected,
                "predicted": predicted,
                "absolute_error": abs_error,
                "probabilities": raw["probabilities"],
                "confidence": raw.get("confidence"),
                "legend": raw.get("legend"),
            }

        else:
            raise ValueError(f"Unknown case type: {case_type!r}")

        case_results.append(record)
    print()
    choice_accuracy = (
        choice_correct / choice_total if choice_total else None
    )
    noul_accuracy = (
        noul_correct / noul_total if noul_total else None
    )
    score_mae = (
        sum(score_errors) / len(score_errors) if score_errors else None
    )

    summary = {
        "choice": {
            "correct": choice_correct,
            "total": choice_total,
            "accuracy": choice_accuracy,
        },
        "noul": {
            "correct": noul_correct,
            "total": noul_total,
            "accuracy": noul_accuracy,
        },
        "score": {
            "total": len(score_errors),
            "mae": score_mae,
        },
        "total_cases": len(cases),
        "failure_count": len(failures),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_file": str(args.cases),
        "model": getattr(engine, "model_name", None)
        or getattr(engine, "model_id", None)
        or "MoritzLaurer/ModernBERT-large-zeroshot-v2.0",
        "summary": summary,
        "results": case_results,
        "failures": failures,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========================================")
    if choice_total:
        print(
            f"Choice accuracy: {choice_correct}/{choice_total} = "
            f"{choice_accuracy:.1%}"
        )
    if noul_total:
        print(
            f"Noul accuracy:   {noul_correct}/{noul_total} = "
            f"{noul_accuracy:.1%}"
        )
    if score_errors:
        print(f"Score MAE:       {score_mae:.3f}")
    print(f"Total cases:     {len(cases)}")
    print(f"Failures:        {len(failures)}")
    print(f"Saved results:   {output_path}")

    if failures:
        print("\nFailures")
        print("----------------------------------------")
        for failure in failures:
            print(f"\nID:       {failure['id']}")
            print(f"Expected: {failure['expected']}")
            print(f"Got:      {failure['predicted']}")

            if failure["type"] == "choice":
                print("Probabilities:")
                for label, probability in sorted(
                    failure["probabilities"].items(),
                    key=lambda item: item[1],
                    reverse=True,
                ):
                    print(f"  {label:<25} {probability:.4f}")
            elif failure["type"] == "noul":
                print(f"P(true):  {failure['p_true']:.4f}")


if __name__ == "__main__":
    main()
