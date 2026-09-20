from pathlib import Path
import re

from opendecision.engine import OpenDecisionEngine


CLAIM_PATH = Path(__file__).parent / "sample_claim.txt"
TOP_K_EVIDENCE = 4


CASES = [
    {
        "id": "independent_liability_support",
        "proposition": (
            "Liability is supported by evidence beyond the claimant's own statement."
        ),
        "expected": "supports",
    },
    {
        "id": "prompt_medical_treatment",
        "proposition": (
            "The claimant sought medical treatment within 24 hours of the collision."
        ),
        "expected": "supports",
    },
    {
        "id": "serious_injury_documented",
        "proposition": (
            "A fracture, neurological injury, or hospitalization was documented."
        ),
        "expected": "contradicts",
    },
    {
        "id": "preexisting_neck_condition",
        "proposition": (
            "The file contains evidence of a pre-existing neck-related condition."
        ),
        "expected": "supports",
    },
    {
        "id": "prior_active_treatment",
        "proposition": (
            "The claimant's prior neck condition required imaging, "
            "prescription medication, or active treatment."
        ),
        "expected": "contradicts",
    },
    {
        "id": "lost_wages_fully_supported",
        "proposition": (
            "The full claimed lost-wage amount is supported by employer records."
        ),
        "expected": "contradicts",
    },
    {
        "id": "rental_fully_supported",
        "proposition": (
            "The entire claimed rental period is clearly supported by "
            "the documented vehicle repair dates."
        ),
        "expected": "contradicts",
    },
    {
        "id": "documents_outstanding",
        "proposition": (
            "Additional documentation is still outstanding before the "
            "claim file is complete."
        ),
        "expected": "supports",
    },
    {
        "id": "medical_expenses_documented",
        "proposition": (
            "The claimed emergency-room and physical-therapy expenses "
            "are supported by invoices in the file."
        ),
        "expected": "supports",
    },
    {
        "id": "collision_accounts_consistent",
        "proposition": (
            "The claimant statement, police report, and witness evidence "
            "are consistent about the basic collision mechanism."
        ),
        "expected": "supports",
    },
]


def split_sections(document: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^={20,}\s*$\n^([^\n]+?)\s*$\n^={20,}\s*$",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(document))
    sections = []

    if matches:
        header = document[: matches[0].start()].strip()

        if header:
            sections.append(("CLAIM HEADER", header))

    for i, match in enumerate(matches):
        title = match.group(1).strip()

        start = match.end()

        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(document)
        )

        body = document[start:end].strip()

        if body:
            sections.append((title, body))

    return sections


def scan_sections(
    engine: OpenDecisionEngine,
    sections: list[tuple[str, str]],
    proposition: str,
):
    """
    Cheap first-stage evidence scan.

    Each section is independently classified as:
      supports
      contradicts
      insufficient

    All sections are processed as a batch.
    """

    sequences = [
        f"{title}\n\n{body}"
        for title, body in sections
    ]

    candidate_labels = [
        "supports",
        "contradicts",
        "is insufficient to determine",
    ]

    results = engine.classifier(
        sequences,
        candidate_labels=candidate_labels,
        hypothesis_template=(
            f'This section {{}} the proposition: "{proposition}"'
        ),
        multi_label=False,
        batch_size=8,
    )

    rows = []

    for (title, body), result in zip(sections, results):
        scores = dict(
            zip(
                result["labels"],
                result["scores"],
            )
        )

        support = float(scores["supports"])
        contradict = float(scores["contradicts"])
        insufficient = float(
            scores["is insufficient to determine"]
        )

        if support >= contradict and support >= insufficient:
            relation = "supports"
        elif contradict >= support and contradict >= insufficient:
            relation = "contradicts"
        else:
            relation = "insufficient"

        # Evidence strength is high when the model thinks the
        # section is useful either for or against the proposition.
        evidence_strength = 1.0 - insufficient

        rows.append(
            {
                "title": title,
                "body": body,
                "relation": relation,
                "support": support,
                "contradict": contradict,
                "insufficient": insufficient,
                "strength": evidence_strength,
            }
        )

    rows.sort(
        key=lambda row: row["strength"],
        reverse=True,
    )

    return rows


def build_evidence_bundle(rows):
    parts = []

    for row in rows[:TOP_K_EVIDENCE]:
        parts.append(
            f"""
SOURCE: {row['title']}
Section-level evidence assessment:
supports={row['support']:.3f}
contradicts={row['contradict']:.3f}
insufficient={row['insufficient']:.3f}

{row['body']}
""".strip()
        )

    return "\n\n" + ("\n\n" + "-" * 60 + "\n\n").join(parts)


def final_decision(
    engine: OpenDecisionEngine,
    proposition: str,
    evidence: str,
):
    return engine.choice(
        state=evidence,
        instructions=(
            "Based only on the supplied document evidence, "
            f'what is the relationship to this proposition: "{proposition}"'
        ),
        criteria={
            "supports": (
                "The available document evidence supports the proposition."
            ),
            "contradicts": (
                "The available document evidence contradicts the proposition."
            ),
            "unclear": (
                "The evidence is insufficient, ambiguous, or conflicting, "
                "so the proposition cannot be determined."
            ),
        },
    )


def main():
    claim = CLAIM_PATH.read_text(encoding="utf-8")
    sections = split_sections(claim)

    print(f"Characters: {len(claim):,}")
    print(f"Sections:   {len(sections)}")

    engine = OpenDecisionEngine()

    correct = 0

    for index, case in enumerate(CASES, start=1):
        print("\n" + "=" * 78)
        print(f"[{index}/{len(CASES)}] {case['id']}")
        print("=" * 78)

        print(f"\nProposition:\n{case['proposition']}")

        rows = scan_sections(
            engine,
            sections,
            case["proposition"],
        )

        print("\nStrongest evidence sections:")

        for row in rows[:TOP_K_EVIDENCE]:
            print(
                f"  {row['title']:<32} "
                f"{row['relation']:<12} "
                f"S={row['support']:.3f} "
                f"C={row['contradict']:.3f} "
                f"I={row['insufficient']:.3f}"
            )

        evidence = build_evidence_bundle(rows)

        result = final_decision(
            engine,
            case["proposition"],
            evidence,
        )

        predicted = result["choice"]
        expected = case["expected"]
        passed = predicted == expected

        correct += int(passed)

        print("\nFinal decision:")
        print(f"  Expected:  {expected}")
        print(f"  Predicted: {predicted}")
        print(f"  Result:    {'✓' if passed else '✗'}")

        print("\nProbabilities:")

        for label, probability in sorted(
            result["probabilities"].items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(
                f"  {label:<14} "
                f"{probability:.3f}"
            )

    total = len(CASES)

    print("\n" + "=" * 78)
    print(
        f"EVIDENCE SCAN → DECIDE: "
        f"{correct}/{total} = {correct / total:.1%}"
    )
    print("WHOLE-DOCUMENT NOUL BASELINE: 5/10 = 50.0%")
    print("=" * 78)


if __name__ == "__main__":
    main()