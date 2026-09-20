from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from opendecision.engine import OpenDecisionEngine

from questions import CHOICE_QUESTIONS, NOUL_QUESTIONS, SCORE_QUESTIONS


DEFAULT_DOCUMENT = Path("tests/GDPR_wiki_test.txt")
DEFAULT_MODEL = "tasksource/ModernBERT-large-nli"


def normalize_exported_text(text: str) -> str:
    # The supplied Wikipedia export stores line breaks as the two literal
    # characters backslash+n rather than actual newline characters.
    return text.replace("\\n", "\n")


def split_wiki_sections(text: str) -> list[dict[str, str]]:
    heading = re.compile(r"^(={2,})\s*(.*?)\s*\1$")
    sections = []
    title = "INTRODUCTION"
    body: list[str] = []

    def append_section() -> None:
        content = "\n".join(line for line in body if line.strip()).strip()
        if content:
            sections.append(
                {
                    "id": title,
                    "text": f"{title}\n\n{content}",
                }
            )

    for line in normalize_exported_text(text).splitlines():
        match = heading.match(line.strip())

        if match:
            append_section()
            title = match.group(2)
            body = []
        else:
            body.append(line)

    append_section()
    return sections


def evidence_bundle(
    engine: OpenDecisionEngine,
    sections: list[dict[str, str]],
    proposition: str,
    contradiction: str,
    top_k: int,
) -> tuple[str, list[str]]:
    ranked = engine.rank_evidence(
        evidence=sections,
        proposition=proposition,
        contradiction=contradiction,
        top_k=top_k,
    )
    return (
        "\n\n---\n\n".join(row["text"] for row in ranked),
        [row["id"] for row in ranked],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    document = args.document.read_text(encoding="utf-8")
    sections = split_wiki_sections(document)
    engine = OpenDecisionEngine(model=args.model)
    rows: list[dict[str, Any]] = []

    for question_id, question in NOUL_QUESTIONS.items():
        bundle, sources = evidence_bundle(
            engine,
            sections,
            question["proposition"],
            question["contradiction"],
            args.top_k,
        )
        result = engine.relation(
            state=bundle,
            proposition=question["proposition"],
            contradiction=question["contradiction"],
        )
        predicted = result["relation"] == "supports"
        rows.append(
            {
                "id": question_id,
                "type": "noul_via_relation",
                "expected": question["expected"],
                "predicted": predicted,
                "relation": result["relation"],
                "correct": predicted == question["expected"],
                "metric": result["scores"]["supports"],
                "sources": sources,
            }
        )

    for question_id, question in CHOICE_QUESTIONS.items():
        bundle, sources = evidence_bundle(
            engine,
            sections,
            question["retrieval"],
            f"The passage is unrelated to: {question['instructions']}",
            args.top_k,
        )
        result = engine.choice(
            state=bundle,
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
                "sources": sources,
            }
        )

    for question_id, question in SCORE_QUESTIONS.items():
        bundle, sources = evidence_bundle(
            engine,
            sections,
            question["retrieval"],
            f"The passage is unrelated to: {question['instructions']}",
            args.top_k,
        )
        result = engine.score(
            state=bundle,
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
                "sources": sources,
            }
        )

    objective_rows = [
        row for row in rows if row["type"] in {"noul_via_relation", "choice"}
    ]
    objective_correct = sum(row["correct"] for row in objective_rows)
    payload = {
        "document": str(args.document),
        "model": args.model,
        "characters": len(document),
        "sections": len(sections),
        "top_k": args.top_k,
        "summary": {
            "objective_correct": objective_correct,
            "objective_total": len(objective_rows),
            "objective_accuracy": objective_correct / len(objective_rows),
            "score_questions": len(rows) - len(objective_rows),
        },
        "results": rows,
    }

    for row in rows:
        marker = "PASS" if row["correct"] else "FAIL"
        print(
            f"{marker:<4} {row['id']:<24} {row['type']:<17} "
            f"expected={str(row['expected']):<11} "
            f"predicted={str(row['predicted']):<11} "
            f"metric={row['metric']:.3f} "
            f"sources={', '.join(row['sources'])}"
        )

    print(
        f"\nRetrieved sections: {len(sections)}; "
        f"objective Noul/Choice accuracy: "
        f"{objective_correct}/{len(objective_rows)} "
        f"= {objective_correct / len(objective_rows):.1%}; "
        f"Score judgments reported separately"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
