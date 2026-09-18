from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze A/B complementarity on OpenDecision Choice results."
    )
    parser.add_argument(
        "--ab",
        type=Path,
        default=Path(
            "benchmarks/results/opendecision_original_holdout_universal_ab.json"
        ),
        help="Universal A/B result JSON.",
    )
    parser.add_argument(
        "--routed",
        type=Path,
        default=Path(
            "benchmarks/results/opendecision_meta_router_holdout.json"
        ),
        help="Optional automatic-router result JSON.",
    )
    args = parser.parse_args()

    data = load_json(args.ab)

    a_rows = {
        row["id"]: row
        for row in data["details"]["A"]["results"]
    }
    b_rows = {
        row["id"]: row
        for row in data["details"]["B"]["results"]
    }

    if set(a_rows) != set(b_rows):
        raise RuntimeError("A and B result files do not contain identical case IDs.")

    ids = sorted(a_rows)
    total = len(ids)

    counts = Counter()
    by_domain = defaultdict(Counter)

    a_only_cases = []
    b_only_cases = []
    both_wrong_cases = []

    for case_id in ids:
        a = a_rows[case_id]
        b = b_rows[case_id]

        a_ok = bool(a["correct"])
        b_ok = bool(b["correct"])

        if a_ok and b_ok:
            bucket = "both_correct"
        elif a_ok and not b_ok:
            bucket = "a_only"
            a_only_cases.append(case_id)
        elif not a_ok and b_ok:
            bucket = "b_only"
            b_only_cases.append(case_id)
        else:
            bucket = "both_wrong"
            both_wrong_cases.append(case_id)

        counts[bucket] += 1
        domain = a.get("domain") or "unknown"
        by_domain[domain][bucket] += 1
        by_domain[domain]["total"] += 1

    a_correct = counts["both_correct"] + counts["a_only"]
    b_correct = counts["both_correct"] + counts["b_only"]
    oracle_correct = (
        counts["both_correct"]
        + counts["a_only"]
        + counts["b_only"]
    )

    print("A/B complementarity")
    print("============================================================")
    print(f"Total cases:       {total}")
    print(f"Both correct:      {counts['both_correct']:>3}")
    print(f"A only correct:    {counts['a_only']:>3}")
    print(f"B only correct:    {counts['b_only']:>3}")
    print(f"Both wrong:        {counts['both_wrong']:>3}")
    print()
    print(f"Universal A:       {a_correct}/{total} = {a_correct/total:.1%}")
    print(f"Universal B:       {b_correct}/{total} = {b_correct/total:.1%}")
    print(
        f"Per-case A/B oracle:{oracle_correct}/{total} = "
        f"{oracle_correct/total:.1%}"
    )
    print(
        f"Headroom over A:   +{oracle_correct - a_correct} cases "
        f"(+{(oracle_correct-a_correct)/total:.1%})"
    )
    print()
    print(
        f"A/B disagreement:  "
        f"{counts['a_only'] + counts['b_only']}/{total} = "
        f"{(counts['a_only'] + counts['b_only'])/total:.1%}"
    )

    # McNemar exact two-sided binomial test without scipy.
    b = counts["a_only"]
    c = counts["b_only"]
    n = b + c

    if n:
        from math import comb

        k = min(b, c)
        one_tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
        p_value = min(1.0, 2 * one_tail)

        print(
            f"McNemar discordant pairs: A-only={b}, B-only={c}"
        )
        print(f"Exact two-sided p-value:  {p_value:.4f}")

    print("\nBy domain")
    print("============================================================")
    print(
        f"{'Domain':<28} {'Both+':>6} {'A only':>7} "
        f"{'B only':>7} {'Both-':>6} {'Oracle':>7}"
    )

    for domain in sorted(by_domain):
        d = by_domain[domain]
        oracle = (
            d["both_correct"]
            + d["a_only"]
            + d["b_only"]
        )
        print(
            f"{domain:<28} "
            f"{d['both_correct']:>6} "
            f"{d['a_only']:>7} "
            f"{d['b_only']:>7} "
            f"{d['both_wrong']:>6} "
            f"{oracle:>2}/{d['total']:<4}"
        )

    print("\nCases where B rescues A")
    print("============================================================")
    for case_id in b_only_cases:
        a = a_rows[case_id]
        b_row = b_rows[case_id]
        print(
            f"{case_id}: "
            f"A={a['predicted']}  "
            f"B={b_row['predicted']}  "
            f"expected={b_row['expected']}"
        )

    print("\nCases where A rescues B")
    print("============================================================")
    for case_id in a_only_cases:
        a = a_rows[case_id]
        b_row = b_rows[case_id]
        print(
            f"{case_id}: "
            f"A={a['predicted']}  "
            f"B={b_row['predicted']}  "
            f"expected={a['expected']}"
        )

    print("\nCases neither compiler solves")
    print("============================================================")
    for case_id in both_wrong_cases:
        a = a_rows[case_id]
        b_row = b_rows[case_id]
        print(
            f"{case_id}: "
            f"A={a['predicted']}  "
            f"B={b_row['predicted']}  "
            f"expected={a['expected']}"
        )

    if args.routed.exists():
        routed = load_json(args.routed)
        routed_rows = {row["id"]: row for row in routed["results"]}

        if set(routed_rows) == set(ids):
            router_correct = sum(
                bool(routed_rows[i]["final_correct"])
                for i in ids
            )

            router_oracle_hits = 0
            router_missed_recoverable = 0

            for i in ids:
                a_ok = bool(a_rows[i]["correct"])
                b_ok = bool(b_rows[i]["correct"])
                recoverable = a_ok or b_ok
                r_ok = bool(routed_rows[i]["final_correct"])

                if recoverable and r_ok:
                    router_oracle_hits += 1
                elif recoverable and not r_ok:
                    router_missed_recoverable += 1

            print("\nAutomatic router vs per-case A/B oracle")
            print("============================================================")
            print(
                f"Automatic router:   {router_correct}/{total} = "
                f"{router_correct/total:.1%}"
            )
            print(
                f"Per-case A/B oracle:{oracle_correct}/{total} = "
                f"{oracle_correct/total:.1%}"
            )
            print(
                f"Recoverable cases missed by router: "
                f"{router_missed_recoverable}"
            )


if __name__ == "__main__":
    main()
