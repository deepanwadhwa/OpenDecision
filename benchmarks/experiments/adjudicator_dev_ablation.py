from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine


PROFILE_A = {
    "name": "A",
    "premise": "state",
    "candidate": "description",
    "hypothesis": "question",
}

PROFILE_B = {
    "name": "B",
    "premise": "state",
    "candidate": "label_description",
    "hypothesis": "default",
}


PREMISE_MODES = ("state", "state_question")
CANDIDATE_MODES = ("description", "label", "label_description")
HYPOTHESIS_MODES = ("default", "question")

ADJUDICATOR_PROFILES = [
    {
        "name": f"P={premise}__C={candidate}__H={hypothesis}",
        "premise": premise,
        "candidate": candidate,
        "hypothesis": hypothesis,
    }
    for premise, candidate, hypothesis in itertools.product(
        PREMISE_MODES,
        CANDIDATE_MODES,
        HYPOTHESIS_MODES,
    )
]


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
                    f"{path}:{line_number}: expected Choice case"
                )

            cases.append(case)

    return cases


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


def build_premise(
    state: Any,
    instructions: str,
    mode: str,
) -> str:
    serialized = serialize_state(state)

    if mode == "state":
        return serialized

    if mode == "state_question":
        return f"{serialized}\n\nQuestion: {instructions}"

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
            candidate = (
                f"{nice}: {description}"
                if description
                else nice
            )

        else:
            raise ValueError(mode)

        if candidate in reverse:
            candidate = f"{nice}: {candidate}"

        rendered.append(candidate)
        reverse[candidate] = label

    return rendered, reverse


def classify_profile(
    engine: OpenDecisionEngine,
    *,
    state: Any,
    instructions: str,
    criteria: dict[str, str | None],
    profile: dict[str, str],
) -> dict[str, Any]:
    sequence = build_premise(
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

    raw = engine.classifier(sequence, **kwargs)

    probabilities = {
        reverse[rendered]: float(score)
        for rendered, score in zip(raw["labels"], raw["scores"])
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
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate semantic adjudication of A/B compiler disagreements "
            "on the OpenDecision development set."
        )
    )

    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(
            "benchmarks/opendecision_original/dev.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "benchmarks/results/"
            "opendecision_adjudicator_dev_ablation.json"
        ),
    )

    args = parser.parse_args()

    cases = load_cases(args.cases)
    engine = OpenDecisionEngine()

    print(f"Loaded {len(cases)} development cases.")
    print("Caching compiler A and B predictions...\n")

    cached: dict[str, dict[str, Any]] = {}

    for i, case in enumerate(cases, start=1):
        result_a = classify_profile(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
            profile=PROFILE_A,
        )

        result_b = classify_profile(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
            profile=PROFILE_B,
        )

        cached[case["id"]] = {
            "A": result_a,
            "B": result_b,
        }

        print(
            f"\r[{i:>3}/{len(cases)}] {case['id']:<32}",
            end="",
            flush=True,
        )

    print("\n")

    overlap = Counter()
    disagreement_cases = []

    for case in cases:
        case_id = case["id"]
        a_answer = cached[case_id]["A"]["predicted"]
        b_answer = cached[case_id]["B"]["predicted"]

        a_ok = a_answer == case["expected"]
        b_ok = b_answer == case["expected"]

        if a_ok and b_ok:
            overlap["both_correct"] += 1
        elif a_ok:
            overlap["a_only"] += 1
        elif b_ok:
            overlap["b_only"] += 1
        else:
            overlap["both_wrong"] += 1

        if a_answer == b_answer:
            overlap["answer_agree"] += 1
            if a_ok:
                overlap["agree_correct"] += 1
            else:
                overlap["agree_wrong"] += 1
        else:
            overlap["answer_disagree"] += 1

            if a_ok and not b_ok:
                kind = "A_only"
            elif b_ok and not a_ok:
                kind = "B_only"
            else:
                kind = "both_wrong"

            disagreement_cases.append(
                {
                    "case": case,
                    "answer_a": a_answer,
                    "answer_b": b_answer,
                    "a_correct": a_ok,
                    "b_correct": b_ok,
                    "kind": kind,
                }
            )

    universal_a = overlap["both_correct"] + overlap["a_only"]
    universal_b = overlap["both_correct"] + overlap["b_only"]
    oracle = (
        overlap["both_correct"]
        + overlap["a_only"]
        + overlap["b_only"]
    )

    recoverable_disagreements = sum(
        1
        for row in disagreement_cases
        if row["kind"] in ("A_only", "B_only")
    )

    unrecoverable_disagreements = (
        len(disagreement_cases) - recoverable_disagreements
    )

    print("A/B structure")
    print("-----------------------------------------------------------------------")
    print(f"Both correct:                {overlap['both_correct']}")
    print(f"A only correct:              {overlap['a_only']}")
    print(f"B only correct:              {overlap['b_only']}")
    print(f"Both wrong:                  {overlap['both_wrong']}")
    print()
    print(f"A/B same answer:             {overlap['answer_agree']}")
    print(f"  same + correct:            {overlap['agree_correct']}")
    print(f"  same + wrong:              {overlap['agree_wrong']}")
    print(f"A/B different answers:       {overlap['answer_disagree']}")
    print(f"  recoverable disagreements: {recoverable_disagreements}")
    print(f"  both-wrong disagreements:  {unrecoverable_disagreements}")
    print()

    total_adj_calls = (
        len(disagreement_cases) * len(ADJUDICATOR_PROFILES)
    )

    print(
        f"Running {len(disagreement_cases)} A/B disagreements × "
        f"{len(ADJUDICATOR_PROFILES)} adjudicator profiles = "
        f"{total_adj_calls} adjudicator decisions"
    )

    stats = {
        p["name"]: {
            "total_cases": len(cases),
            "adjudicator_calls": 0,
            "final_correct": overlap["agree_correct"],
            "recoverable_disagreement_total": 0,
            "recoverable_disagreement_correct": 0,
            "all_disagreement_correct": 0,
            "selected_A": 0,
            "selected_B": 0,
        }
        for p in ADJUDICATOR_PROFILES
    }

    rows = []
    completed = 0

    for item in disagreement_cases:
        case = item["case"]
        answer_a = item["answer_a"]
        answer_b = item["answer_b"]

        pair_criteria = disputed_criteria(
            case,
            answer_a,
            answer_b,
        )

        row = {
            "id": case["id"],
            "domain": case.get("domain"),
            "expected": case["expected"],
            "answer_A": answer_a,
            "answer_B": answer_b,
            "A_correct": item["a_correct"],
            "B_correct": item["b_correct"],
            "kind": item["kind"],
            "profiles": {},
        }

        for profile in ADJUDICATOR_PROFILES:
            completed += 1
            name = profile["name"]

            adjudicated = classify_profile(
                engine,
                state=case["state"],
                instructions=case["instructions"],
                criteria=pair_criteria,
                profile=profile,
            )

            final_answer = adjudicated["predicted"]
            final_correct = final_answer == case["expected"]

            if final_answer == answer_a:
                selected = "A"
            elif final_answer == answer_b:
                selected = "B"
            else:
                raise RuntimeError(
                    "Adjudicator returned an answer outside the A/B pair."
                )

            s = stats[name]
            s["adjudicator_calls"] += 1
            s["final_correct"] += int(final_correct)
            s["all_disagreement_correct"] += int(final_correct)
            s[f"selected_{selected}"] += 1

            if item["kind"] in ("A_only", "B_only"):
                s["recoverable_disagreement_total"] += 1
                s["recoverable_disagreement_correct"] += int(
                    final_correct
                )

            row["profiles"][name] = {
                "selected": selected,
                "predicted": final_answer,
                "correct": final_correct,
                "probabilities": adjudicated["probabilities"],
            }

            print(
                f"\r[{completed:>4}/{total_adj_calls}] "
                f"{case['id']:<30} {name:<55}",
                end="",
                flush=True,
            )

        rows.append(row)

    print("\n")

    ranking = []

    for profile in ADJUDICATOR_PROFILES:
        name = profile["name"]
        s = stats[name]

        final_accuracy = (
            s["final_correct"] / len(cases)
        )

        recoverable_accuracy = (
            s["recoverable_disagreement_correct"]
            / s["recoverable_disagreement_total"]
            if s["recoverable_disagreement_total"]
            else 0.0
        )

        disagreement_accuracy = (
            s["all_disagreement_correct"]
            / len(disagreement_cases)
            if disagreement_cases
            else 0.0
        )

        ranking.append(
            {
                "profile": name,
                **s,
                "final_accuracy": final_accuracy,
                "recoverable_disagreement_accuracy": (
                    recoverable_accuracy
                ),
                "all_disagreement_accuracy": (
                    disagreement_accuracy
                ),
            }
        )

    ranking.sort(
        key=lambda x: (
            -x["final_accuracy"],
            -x["recoverable_disagreement_accuracy"],
            x["profile"],
        )
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": "semantic_ab_adjudicator_dev_ablation",
        "cases_file": str(args.cases),
        "case_count": len(cases),
        "profile_A": PROFILE_A,
        "profile_B": PROFILE_B,
        "baselines": {
            "both_correct": overlap["both_correct"],
            "A_only": overlap["a_only"],
            "B_only": overlap["b_only"],
            "both_wrong": overlap["both_wrong"],
            "answer_agree": overlap["answer_agree"],
            "agree_correct": overlap["agree_correct"],
            "agree_wrong": overlap["agree_wrong"],
            "answer_disagree": overlap["answer_disagree"],
            "recoverable_disagreements": (
                recoverable_disagreements
            ),
            "unrecoverable_disagreements": (
                unrecoverable_disagreements
            ),
            "universal_A": {
                "correct": universal_a,
                "total": len(cases),
                "accuracy": universal_a / len(cases),
            },
            "universal_B": {
                "correct": universal_b,
                "total": len(cases),
                "accuracy": universal_b / len(cases),
            },
            "per_case_AB_oracle": {
                "correct": oracle,
                "total": len(cases),
                "accuracy": oracle / len(cases),
            },
        },
        "ranking": ranking,
        "disagreement_results": rows,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("Baselines")
    print("-----------------------------------------------------------------------")
    print(
        f"Universal A:          {universal_a}/{len(cases)} = "
        f"{universal_a / len(cases):.1%}"
    )
    print(
        f"Universal B:          {universal_b}/{len(cases)} = "
        f"{universal_b / len(cases):.1%}"
    )
    print(
        f"Per-case A/B oracle:  {oracle}/{len(cases)} = "
        f"{oracle / len(cases):.1%}"
    )

    print("\nAdjudicator ranking")
    print(
        "------------------------------------------------------------------------------------------------"
    )
    print(
        f"{'Profile':<57} "
        f"{'Recover':>9} {'Disagree':>9} {'Final':>8} {'A/B picks':>10}"
    )
    print(
        "------------------------------------------------------------------------------------------------"
    )

    for r in ranking:
        print(
            f"{r['profile']:<57} "
            f"{r['recoverable_disagreement_accuracy']:>8.1%} "
            f"{r['all_disagreement_accuracy']:>8.1%} "
            f"{r['final_accuracy']:>7.1%} "
            f"{r['selected_A']:>3}/{r['selected_B']:<3}"
        )

    winner = ranking[0]

    print("\nRecommended adjudicator compiler from DEV")
    print("-----------------------------------------------------------------------")
    print(winner["profile"])
    print(
        "Recoverable disagreement selection: "
        f"{winner['recoverable_disagreement_correct']}/"
        f"{winner['recoverable_disagreement_total']} = "
        f"{winner['recoverable_disagreement_accuracy']:.1%}"
    )
    print(
        f"End-to-end accuracy: "
        f"{winner['final_correct']}/{len(cases)} = "
        f"{winner['final_accuracy']:.1%}"
    )
    print(
        f"Adjudicator invoked on "
        f"{winner['adjudicator_calls']}/{len(cases)} requests = "
        f"{winner['adjudicator_calls']/len(cases):.1%}"
    )

    print(f"\nSaved results: {args.output}")


if __name__ == "__main__":
    main()
