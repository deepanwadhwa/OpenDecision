from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine


PROFILES = {
    "A": {
        "premise": "state",
        "candidate": "description",
        "hypothesis": "question",
    },
    "B": {
        "premise": "state",
        "candidate": "label_description",
        "hypothesis": "default",
    },
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if case.get("type") != "choice":
                raise ValueError(
                    f"{path}:{line_number}: expected Choice case, got {case.get('type')!r}"
                )
            cases.append(case)
    return cases


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def serialize_state(state: Any) -> str:
    if isinstance(state, str):
        return state
    return json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def natural_label(label: str) -> str:
    return label.replace("_", " ")


def render_candidates(
    criteria: dict[str, str | None],
    mode: str,
) -> tuple[list[str], dict[str, str]]:
    rendered = []
    reverse = {}

    for label, description in criteria.items():
        nice = natural_label(label)

        if mode == "description":
            candidate = description or nice
        elif mode == "label_description":
            candidate = f"{nice}: {description}" if description else nice
        else:
            raise ValueError(mode)

        if candidate in reverse:
            candidate = f"{nice}: {candidate}"

        rendered.append(candidate)
        reverse[candidate] = label

    return rendered, reverse


def classify(
    engine: OpenDecisionEngine,
    case: dict[str, Any],
    profile_name: str,
) -> dict[str, Any]:
    profile = PROFILES[profile_name]
    sequence = serialize_state(case["state"])

    candidates, reverse = render_candidates(
        case["criteria"],
        profile["candidate"],
    )

    kwargs: dict[str, Any] = {
        "candidate_labels": candidates,
        "multi_label": False,
    }

    if profile["hypothesis"] == "question":
        kwargs["hypothesis_template"] = (
            f'The answer to the question "{case["instructions"]}" is {{}}.'
        )

    raw = engine.classifier(sequence, **kwargs)

    probabilities = {
        reverse[label]: float(score)
        for label, score in zip(raw["labels"], raw["scores"])
    }

    probabilities = {
        label: probabilities[label]
        for label in case["criteria"]
    }

    predicted = max(probabilities, key=probabilities.get)

    return {
        "predicted": predicted,
        "correct": predicted == case["expected"],
        "probabilities": probabilities,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("benchmarks/opendecision_original/holdout.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "benchmarks/results/opendecision_original_holdout_universal_ab.json"
        ),
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    engine = OpenDecisionEngine()

    summary = {}
    all_results = {}

    for profile_name in ("A", "B"):
        correct = 0
        results = []
        failures = []

        print(f"\nRunning universal Profile {profile_name} on {len(cases)} holdout cases...")

        for index, case in enumerate(cases, start=1):
            result = classify(engine, case, profile_name)
            correct += int(result["correct"])

            record = {
                "id": case["id"],
                "domain": case.get("domain"),
                "expected": case["expected"],
                "predicted": result["predicted"],
                "correct": result["correct"],
                "probabilities": result["probabilities"],
            }

            results.append(record)
            if not result["correct"]:
                failures.append(record)

            print(
                f"\r[{index:>3}/{len(cases)}] {case['id']:<32}",
                end="",
                flush=True,
            )

        print()

        accuracy = correct / len(cases)

        summary[profile_name] = {
            "correct": correct,
            "total": len(cases),
            "accuracy": accuracy,
            "failure_count": len(failures),
        }

        all_results[profile_name] = {
            "results": results,
            "failures": failures,
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": "universal_profile_A_vs_B_holdout",
        "cases_file": str(args.cases),
        "cases_sha256": sha256_file(args.cases),
        "profiles": PROFILES,
        "summary": summary,
        "details": all_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========================================")
    for profile_name in ("A", "B"):
        stats = summary[profile_name]
        print(
            f"Universal {profile_name}: "
            f"{stats['correct']}/{stats['total']} = "
            f"{stats['accuracy']:.1%}"
        )

    print(f"\nSaved results: {args.output}")


if __name__ == "__main__":
    main()
