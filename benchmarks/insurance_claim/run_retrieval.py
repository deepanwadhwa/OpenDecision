from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine

from run_atomic import DEFAULT_CASES, load_cases


HERE = Path(__file__).parent
CLAIM_PATH = HERE.parent.parent / "tests" / "sample_claim.txt"
MODEL = "tasksource/ModernBERT-large-nli"
SOURCE_TO_SECTION = {
    "claim_intake": "CLAIM INTAKE FORM",
    "police_report": "POLICE REPORT SUMMARY",
    "emergency_department": "EMERGENCY DEPARTMENT RECORD",
    "medical_bill": "MEDICAL BILL",
    "physical_therapy_bill": "PHYSICAL THERAPY BILL",
    "employment_statement": "EMPLOYMENT / LOST WAGE STATEMENT",
    "prior_medical_record": "PRIOR MEDICAL RECORD NOTE",
    "adjuster_note": "ADJUSTER INTERNAL NOTE",
    "claimant_demand": "CLAIMANT DEMAND",
    "file_status": "CURRENT FILE STATUS",
}


def split_sections(document: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"^={20,}\s*$\n^([^\n]+?)\s*$\n^={20,}\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(document))
    sections = []

    for index, match in enumerate(matches):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(document)
        )
        title = match.group(1).strip()
        sections.append(
            {
                "id": title,
                "text": f"{title}\n\n{document[start:end].strip()}",
            }
        )

    return sections


def gold_sections(case: dict[str, Any]) -> set[str]:
    return {
        SOURCE_TO_SECTION[source_id.split(":", 1)[0]]
        for source_id in case["source_ids"]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--claim", type=Path, default=CLAIM_PATH)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    sections = split_sections(args.claim.read_text(encoding="utf-8"))
    engine = OpenDecisionEngine(model=args.model)
    rows = []
    relation_items = []

    for case in cases:
        ranked = engine.rank_evidence(
            evidence=sections,
            proposition=case["proposition"],
            contradiction=case["contradiction"],
            top_k=args.top_k,
        )
        expected = gold_sections(case)
        retrieved = {row["id"] for row in ranked}
        found = expected & retrieved
        rows.append(
            {
                "id": case["id"],
                "gold_sections": sorted(expected),
                "retrieved_sections": [row["id"] for row in ranked],
                "recall": len(found) / len(expected),
                "all_gold_retrieved": found == expected,
                "ranking": [
                    {
                        "id": row["id"],
                        "relevance": row["relevance"],
                        "relation": row["relation"],
                    }
                    for row in ranked
                ],
            }
        )
        relation_items.append(
            {
                "state": "\n\n---\n\n".join(
                    row["text"]
                    for row in ranked
                ),
                "proposition": case["proposition"],
                "contradiction": case["contradiction"],
            }
        )

    relations = engine.relations(items=relation_items)

    for case, row, relation in zip(cases, rows, relations):
        row["expected"] = case["expected"]
        row["predicted"] = relation["relation"]
        row["correct"] = row["predicted"] == row["expected"]
        row["relation_scores"] = relation["scores"]

    mean_recall = sum(row["recall"] for row in rows) / len(rows)
    complete = sum(row["all_gold_retrieved"] for row in rows)
    relation_correct = sum(row["correct"] for row in rows)
    payload = {
        "summary": {
            "cases": len(rows),
            "top_k": args.top_k,
            "mean_gold_section_recall": mean_recall,
            "all_gold_retrieved": complete,
            "relation_correct": relation_correct,
            "relation_accuracy": relation_correct / len(rows),
        },
        "results": rows,
    }

    for row in rows:
        marker = "PASS" if row["all_gold_retrieved"] else "MISS"
        print(
            f"{marker:<4} {row['id']:<32} "
            f"recall={row['recall']:.0%} "
            f"relation={row['predicted']:<11} "
            f"top={', '.join(row['retrieved_sections'])}"
        )

    print(
        f"\nRetrieval@{args.top_k}: mean gold-section recall "
        f"{mean_recall:.1%}; all gold found for {complete}/{len(rows)} cases"
    )
    print(
        f"Retrieved-evidence relation: {relation_correct}/{len(rows)} "
        f"= {relation_correct / len(rows):.1%}"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
