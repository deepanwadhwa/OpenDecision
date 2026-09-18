from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine


# Frozen from DEV
PROFILE_A = {
    "premise": "state",
    "candidate": "description",
    "hypothesis": "question",
}

PROFILE_B = {
    "premise": "state",
    "candidate": "label_description",
    "hypothesis": "default",
}

# Winning DEV adjudicator:
# P=state_question__C=label__H=default
ADJUDICATOR = {
    "premise": "state_question",
    "candidate": "label",
    "hypothesis": "default",
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if case.get("type") != "choice":
                raise ValueError(f"{path}:{n}: expected Choice case")
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


def build_premise(state: Any, instructions: str, mode: str) -> str:
    s = serialize_state(state)

    if mode == "state":
        return s

    if mode == "state_question":
        return f"{s}\n\nQuestion: {instructions}"

    raise ValueError(mode)


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
        elif mode == "label":
            candidate = nice
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
    *,
    state: Any,
    instructions: str,
    criteria: dict[str, str | None],
    profile: dict[str, str],
) -> dict[str, Any]:
    premise = build_premise(
        state,
        instructions,
        profile["premise"],
    )

    candidates, reverse = render_candidates(
        criteria,
        profile["candidate"],
    )

    kwargs: dict[str, Any] = {
        "candidate_labels": candidates,
        "multi_label": False,
    }

    if profile["hypothesis"] == "question":
        kwargs["hypothesis_template"] = (
            f'The answer to the question "{instructions}" is {{}}.'
        )

    raw = engine.classifier(premise, **kwargs)

    probabilities = {
        reverse[candidate]: float(score)
        for candidate, score in zip(raw["labels"], raw["scores"])
    }

    probabilities = {
        label: probabilities[label]
        for label in criteria
    }

    predicted = max(probabilities, key=probabilities.get)

    return {
        "predicted": predicted,
        "probabilities": probabilities,
    }


def disputed_criteria(
    case: dict[str, Any],
    answer_a: str,
    answer_b: str,
) -> dict[str, str | None]:
    wanted = {answer_a, answer_b}

    return {
        label: description
        for label, description in case["criteria"].items()
        if label in wanted
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(
            "benchmarks/opendecision_original/holdout.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "benchmarks/results/"
            "opendecision_adjudicator_holdout.json"
        ),
    )

    args = parser.parse_args()

    cases = load_cases(args.cases)
    engine = OpenDecisionEngine()

    total = len(cases)
    final_correct = 0

    answer_agree = 0
    answer_disagree = 0
    agree_correct = 0
    adjudicator_correct = 0
    adjudicator_calls = 0

    results = []
    failures = []

    print("Frozen A+B adjudicator holdout evaluation")
    print("----------------------------------------")
    print("A: state + description + question hypothesis")
    print("B: state + label+description + default hypothesis")
    print("Adjudicator: state+question + labels only + default hypothesis")
    print(f"\nRunning {total} cases...\n")

    for i, case in enumerate(cases, start=1):
        result_a = classify(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
            profile=PROFILE_A,
        )

        result_b = classify(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
            profile=PROFILE_B,
        )

        answer_a = result_a["predicted"]
        answer_b = result_b["predicted"]

        if answer_a == answer_b:
            answer_agree += 1
            final_answer = answer_a
            adjudicated = False
            adjudicator_probs = None

            if final_answer == case["expected"]:
                agree_correct += 1

        else:
            answer_disagree += 1
            adjudicator_calls += 1

            pair_criteria = disputed_criteria(
                case,
                answer_a,
                answer_b,
            )

            adj = classify(
                engine,
                state=case["state"],
                instructions=case["instructions"],
                criteria=pair_criteria,
                profile=ADJUDICATOR,
            )

            final_answer = adj["predicted"]
            adjudicated = True
            adjudicator_probs = adj["probabilities"]

            if final_answer == case["expected"]:
                adjudicator_correct += 1

        correct = final_answer == case["expected"]
        final_correct += int(correct)

        row = {
            "id": case["id"],
            "domain": case.get("domain"),
            "expected": case["expected"],
            "answer_A": answer_a,
            "answer_B": answer_b,
            "A_probabilities": result_a["probabilities"],
            "B_probabilities": result_b["probabilities"],
            "answers_agree": answer_a == answer_b,
            "adjudicated": adjudicated,
            "adjudicator_probabilities": adjudicator_probs,
            "final_answer": final_answer,
            "correct": correct,
        }

        results.append(row)

        if not correct:
            failures.append(row)

        print(
            f"\r[{i:>3}/{total}] {case['id']:<32} "
            f"A={answer_a:<20} B={answer_b:<20}",
            end="",
            flush=True,
        )

    print("\n")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": "frozen_ab_adjudicator_holdout",
        "cases_file": str(args.cases),
        "cases_sha256": sha256_file(args.cases),
        "profile_A": PROFILE_A,
        "profile_B": PROFILE_B,
        "adjudicator_profile": ADJUDICATOR,
        "summary": {
            "total": total,
            "final_correct": final_correct,
            "final_accuracy": final_correct / total,
            "answer_agree": answer_agree,
            "answer_disagree": answer_disagree,
            "agree_correct": agree_correct,
            "adjudicator_calls": adjudicator_calls,
            "adjudicator_correct": adjudicator_correct,
            "adjudicator_disagreement_accuracy": (
                adjudicator_correct / adjudicator_calls
                if adjudicator_calls
                else 0.0
            ),
            "failure_count": len(failures),
        },
        "results": results,
        "failures": failures,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("========================================")
    print(
        f"Final accuracy:       "
        f"{final_correct}/{total} = "
        f"{final_correct / total:.1%}"
    )
    print(
        f"A/B agree:            "
        f"{answer_agree}/{total} = "
        f"{answer_agree / total:.1%}"
    )
    print(
        f"A/B disagree:         "
        f"{answer_disagree}/{total} = "
        f"{answer_disagree / total:.1%}"
    )
    print(
        f"Adjudicator accuracy: "
        f"{adjudicator_correct}/{adjudicator_calls} = "
        f"{adjudicator_correct / adjudicator_calls:.1%}"
        if adjudicator_calls
        else "Adjudicator accuracy: n/a"
    )
    print(f"Failures:             {len(failures)}")
    print(f"\nSaved results: {args.output}")


if __name__ == "__main__":
    main()
