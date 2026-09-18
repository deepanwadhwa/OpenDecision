from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine


PREMISE_MODES = ("state", "state_question")
CANDIDATE_MODES = ("description", "label", "label_description")
HYPOTHESIS_MODES = ("default", "question")

PROFILES = [
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


def load_choice_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if case["type"] == "choice":
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

    raise ValueError(f"Unknown premise mode: {mode}")


def natural_label(label: str) -> str:
    return label.replace("_", " ")


def render_candidates(
    criteria: dict[str, str | None],
    mode: str,
) -> tuple[list[str], dict[str, str]]:
    rendered: list[str] = []
    reverse: dict[str, str] = {}

    for label, description in criteria.items():
        nice = natural_label(label)

        if mode == "description":
            candidate = description or nice

        elif mode == "label":
            candidate = nice

        elif mode == "label_description":
            candidate = f"{nice}: {description}" if description else nice

        else:
            raise ValueError(f"Unknown candidate mode: {mode}")

        # Avoid ambiguous reverse mappings if two descriptions happen to match.
        if candidate in reverse:
            candidate = f"{nice}: {candidate}"

        rendered.append(candidate)
        reverse[candidate] = label

    return rendered, reverse


def build_hypothesis_template(
    instructions: str,
    mode: str,
) -> str | None:
    if mode == "default":
        return None

    if mode == "question":
        return f'The answer to the question "{instructions}" is {{}}.'

    raise ValueError(f"Unknown hypothesis mode: {mode}")


def run_profile(
    engine: OpenDecisionEngine,
    case: dict[str, Any],
    profile: dict[str, str],
) -> dict[str, Any]:
    sequence = build_premise(
        case["state"],
        case["instructions"],
        profile["premise"],
    )

    candidates, reverse = render_candidates(
        case["criteria"],
        profile["candidate"],
    )

    kwargs: dict[str, Any] = {
        "candidate_labels": candidates,
        "multi_label": False,
    }

    hypothesis_template = build_hypothesis_template(
        case["instructions"],
        profile["hypothesis"],
    )
    if hypothesis_template is not None:
        kwargs["hypothesis_template"] = hypothesis_template

    raw = engine.classifier(sequence, **kwargs)

    probabilities = {
        reverse[rendered]: float(score)
        for rendered, score in zip(raw["labels"], raw["scores"])
    }

    # Preserve original criterion ordering in saved JSON.
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


def case_group(case: dict) -> str:
    # New OpenDecision original dataset
    if "domain" in case:
        return case["domain"]

    # Older TypeSafe-derived dataset
    case_id = case["id"]

    mapping = (
        ("ts_date_", "date"),
        ("ts_func_", "function_routing"),
        ("ts_extract_", "preparsed_extraction"),
        ("ts_citation_", "citation"),
        ("ts_hier_", "hierarchical"),
        ("ts_entity_", "entity_alignment"),
    )

    for prefix, group in mapping:
        if case_id.startswith(prefix):
            return group

    return "other"


def accuracy(stats: dict[str, int]) -> float:
    return stats["correct"] / stats["total"] if stats["total"] else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("benchmarks/typesafe_public/cases.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "benchmarks/results/typesafe_public_choice_factorial_ablation.json"
        ),
    )
    args = parser.parse_args()

    cases = load_choice_cases(args.cases)

    if not cases:
        raise RuntimeError(f"No Choice cases found in {args.cases}")

    engine = OpenDecisionEngine()

    overall = {
        p["name"]: {"correct": 0, "total": 0}
        for p in PROFILES
    }

    by_group = defaultdict(
        lambda: {
            p["name"]: {"correct": 0, "total": 0}
            for p in PROFILES
        }
    )

    results: list[dict[str, Any]] = []

    total_runs = len(cases) * len(PROFILES)
    completed = 0

    print(
        f"Running {len(cases)} Choice cases × "
        f"{len(PROFILES)} compiler profiles = {total_runs} decisions"
    )

    for case_index, case in enumerate(cases, start=1):
        group = case_group(case)

        row = {
            "id": case["id"],
            "group": group,
            "expected": case["expected"],
            "profiles": {},
        }

        for profile in PROFILES:
            completed += 1

            result = run_profile(engine, case, profile)
            row["profiles"][profile["name"]] = result

            overall_stats = overall[profile["name"]]
            overall_stats["total"] += 1
            overall_stats["correct"] += int(result["correct"])

            group_stats = by_group[group][profile["name"]]
            group_stats["total"] += 1
            group_stats["correct"] += int(result["correct"])

            print(
                f"\r[{completed:>3}/{total_runs}] "
                f"{case['id']:<24} {profile['name']:<55}",
                end="",
                flush=True,
            )

        results.append(row)

    print()

    overall_serialized = {}
    for profile in PROFILES:
        name = profile["name"]
        stats = overall[name]
        overall_serialized[name] = {
            **stats,
            "accuracy": accuracy(stats),
        }

    groups_serialized = {}
    for group, profile_stats in sorted(by_group.items()):
        groups_serialized[group] = {}
        for profile in PROFILES:
            name = profile["name"]
            stats = profile_stats[name]
            groups_serialized[group][name] = {
                **stats,
                "accuracy": accuracy(stats),
            }

    ranking = sorted(
        (
            {
                "profile": name,
                **stats,
            }
            for name, stats in overall_serialized.items()
        ),
        key=lambda x: (-x["accuracy"], x["profile"]),
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_file": str(args.cases),
        "choice_cases": len(cases),
        "profile_count": len(PROFILES),
        "decision_count": total_runs,
        "factors": {
            "premise": list(PREMISE_MODES),
            "candidate": list(CANDIDATE_MODES),
            "hypothesis": list(HYPOTHESIS_MODES),
        },
        "profiles": PROFILES,
        "ranking": ranking,
        "overall": overall_serialized,
        "by_group": groups_serialized,
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nOverall ranking")
    print("--------------------------------------------------------------------------")
    for rank, row in enumerate(ranking, start=1):
        print(
            f"{rank:>2}. {row['profile']:<55} "
            f"{row['correct']:>2}/{row['total']:<2} "
            f"{row['accuracy']:>7.1%}"
        )

    print("\nBy group")
    print("--------------------------------------------------------------------------")
    for group, profile_stats in groups_serialized.items():
        print(f"\n{group}")
        group_ranking = sorted(
            (
                {
                    "profile": name,
                    **stats,
                }
                for name, stats in profile_stats.items()
            ),
            key=lambda x: (-x["accuracy"], x["profile"]),
        )

        for row in group_ranking:
            print(
                f"  {row['profile']:<55} "
                f"{row['correct']:>2}/{row['total']:<2} "
                f"{row['accuracy']:>7.1%}"
            )

    print(f"\nSaved results: {args.output}")


if __name__ == "__main__":
    main()
