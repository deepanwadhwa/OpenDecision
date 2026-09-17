import json
from dataclasses import dataclass
from pathlib import Path

from opendecision.engine import (
    OpenDecisionEngine,
    _serialize_state,
)


DATASET = Path(__file__).parent / "cases.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


@dataclass(frozen=True)
class Profile:
    name: str

    # "state_question" = current OpenDecision behavior
    # "state_only"     = premise contains only the state
    sequence_mode: str

    # label_description:
    #   billing = Payments, invoices, refunds
    #
    # description_only:
    #   Payments, invoices, refunds
    #
    # label_only:
    #   billing
    candidate_mode: str

    # None means use the HF pipeline default hypothesis template.
    #
    # Otherwise use {question} for the user question
    # and {{}} for the candidate inserted by the pipeline.
    hypothesis_template: str | None


PROFILES = [
    # ---------------------------------------------------------
    # A: EXACT CURRENT BEHAVIOR
    # ---------------------------------------------------------
    Profile(
        name="A_current",
        sequence_mode="state_question",
        candidate_mode="label_description",
        hypothesis_template=None,
    ),

    # ---------------------------------------------------------
    # B: Change ONLY candidate representation.
    # Question remains inside the premise.
    # ---------------------------------------------------------
    Profile(
        name="B_current_description_only",
        sequence_mode="state_question",
        candidate_mode="description_only",
        hypothesis_template=None,
    ),

    # ---------------------------------------------------------
    # C: Keep label + description, but make the state the
    # premise and put the actual question in the hypothesis.
    # ---------------------------------------------------------
    Profile(
        name="C_question_in_hypothesis",
        sequence_mode="state_only",
        candidate_mode="label_description",
        hypothesis_template=(
            'The answer to the question "{question}" is {{}}.'
        ),
    ),

    # ---------------------------------------------------------
    # D: Same as C, except machine-readable labels disappear
    # from the semantic model input whenever descriptions exist.
    # ---------------------------------------------------------
    Profile(
        name="D_question_description_only",
        sequence_mode="state_only",
        candidate_mode="description_only",
        hypothesis_template=(
            'The answer to the question "{question}" is {{}}.'
        ),
    ),

    # ---------------------------------------------------------
    # E: Slightly more natural formulation.
    # ---------------------------------------------------------
    Profile(
        name="E_best_answer_description_only",
        sequence_mode="state_only",
        candidate_mode="description_only",
        hypothesis_template=(
            'Given this information, the best answer to '
            '"{question}" is {{}}.'
        ),
    ),

    # ---------------------------------------------------------
    # F: Tests whether descriptions help at all.
    # ---------------------------------------------------------
    Profile(
        name="F_question_label_only",
        sequence_mode="state_only",
        candidate_mode="label_only",
        hypothesis_template=(
            'The answer to the question "{question}" is {{}}.'
        ),
    ),
]


def load_cases():
    cases = []

    with DATASET.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

    return cases


def naturalize_label(label: str) -> str:
    return label.replace("_", " ")


def render_candidate(
    name: str,
    description: str | None,
    mode: str,
) -> str:

    natural_name = naturalize_label(name)

    if mode == "label_description":
        if description:
            return f"{natural_name} = {description}"

        return natural_name

    if mode == "description_only":
        return description if description else natural_name

    if mode == "label_only":
        return natural_name

    raise ValueError(f"Unknown candidate mode: {mode}")


def build_sequence(
    state,
    instructions: str,
    mode: str,
) -> str:

    state_text = _serialize_state(state)

    if mode == "state_question":
        return f"{state_text}\n\n{instructions}"

    if mode == "state_only":
        return state_text

    raise ValueError(f"Unknown sequence mode: {mode}")


def classify_candidates(
    engine,
    *,
    state,
    instructions,
    criteria,
    profile,
):
    """
    criteria:
        {
            internal_name: optional semantic description
        }

    Returns:
        {
            internal_name: probability
        }
    """

    sequence = build_sequence(
        state,
        instructions,
        profile.sequence_mode,
    )

    rendered_to_internal = {}
    rendered_candidates = []

    for name, description in criteria.items():

        rendered = render_candidate(
            name,
            description,
            profile.candidate_mode,
        )

        # Guard against two criteria turning into exactly the
        # same candidate string.
        if rendered in rendered_to_internal:
            raise ValueError(
                f"Duplicate rendered candidate: {rendered!r}"
            )

        rendered_candidates.append(rendered)
        rendered_to_internal[rendered] = name

    kwargs = {
        "candidate_labels": rendered_candidates,
        "multi_label": False,
    }

    if profile.hypothesis_template is not None:
        kwargs["hypothesis_template"] = (
            profile.hypothesis_template.format(
                question=instructions
            )
        )

    raw = engine.classifier(
        sequence,
        **kwargs,
    )

    probabilities = {}

    for rendered, score in zip(
        raw["labels"],
        raw["scores"],
    ):
        internal = rendered_to_internal[rendered]

        probabilities[internal] = float(score)

    return {
        name: probabilities[name]
        for name in criteria
    }

def evaluate_choice(
    engine,
    case,
    profile,
):
    # A_current must use the REAL production compiler.
    if profile.name == "A_current":
        result = engine.choice(
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
        )

        prediction = result["choice"]
        probabilities = result["probabilities"]

    else:
        probabilities = classify_candidates(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
            profile=profile,
        )

        prediction = max(
            probabilities,
            key=probabilities.get,
        )

    return {
        "correct": prediction == case["expected"],
        "expected": case["expected"],
        "prediction": prediction,
        "probabilities": probabilities,
    }

def evaluate_score(
    engine,
    case,
    profile,
):
    # A_current must use the REAL production compiler.
    if profile.name == "A_current":
        result = engine.score(
            state=case["state"],
            instructions=case["instructions"],
            criteria=case["criteria"],
        )

        prediction = result["score"]
        probabilities = result["probabilities"]

    else:
        criteria = {
            str(index): description
            for index, description in enumerate(
                case["criteria"]
            )
        }

        probabilities = classify_candidates(
            engine,
            state=case["state"],
            instructions=case["instructions"],
            criteria=criteria,
            profile=profile,
        )

        prediction = sum(
            int(index) * probability
            for index, probability
            in probabilities.items()
        )

    expected = float(case["expected"])

    return {
        "prediction": prediction,
        "expected": expected,
        "error": abs(prediction - expected),
        "probabilities": probabilities,
    }
def run_profile(
    engine,
    cases,
    profile,
):
    choice_total = 0
    choice_correct = 0
    choice_failures = []

    score_results = []

    for case in cases:

        # Noul is deliberately excluded.
        #
        # Our Noul implementation performs direct entailment
        # rather than using the Choice compiler templates.
        if case["type"] == "noul":
            continue

        if case["type"] == "choice":

            result = evaluate_choice(
                engine,
                case,
                profile,
            )

            choice_total += 1

            if result["correct"]:
                choice_correct += 1
            else:
                choice_failures.append(
                    {
                        "id": case["id"],
                        **result,
                    }
                )

        elif case["type"] == "score":

            result = evaluate_score(
                engine,
                case,
                profile,
            )

            score_results.append(
                {
                    "id": case["id"],
                    **result,
                }
            )

    choice_accuracy = (
        choice_correct / choice_total
        if choice_total
        else None
    )

    score_mae = (
        sum(x["error"] for x in score_results)
        / len(score_results)
        if score_results
        else None
    )

    return {
        "profile": profile.name,
        "choice_correct": choice_correct,
        "choice_total": choice_total,
        "choice_accuracy": choice_accuracy,
        "score_mae": score_mae,
        "choice_failures": choice_failures,
        "score_results": score_results,
    }


def print_summary(results):
    print()
    print("Template Ablation")
    print("=" * 79)

    print(
        f"{'Profile':<36}"
        f"{'Choice':>12}"
        f"{'Accuracy':>12}"
        f"{'Score MAE':>14}"
    )

    print("-" * 79)

    for result in results:

        choice = (
            f"{result['choice_correct']}/"
            f"{result['choice_total']}"
        )

        accuracy = (
            f"{result['choice_accuracy']:.1%}"
            if result["choice_accuracy"] is not None
            else "-"
        )

        mae = (
            f"{result['score_mae']:.3f}"
            if result["score_mae"] is not None
            else "-"
        )

        print(
            f"{result['profile']:<36}"
            f"{choice:>12}"
            f"{accuracy:>12}"
            f"{mae:>14}"
        )


def print_details(results):
    for result in results:

        print()
        print()
        print(result["profile"])
        print("=" * len(result["profile"]))

        if result["choice_failures"]:
            print()
            print("Choice failures:")

            for failure in result["choice_failures"]:

                print()
                print(
                    f"  {failure['id']}: "
                    f"expected={failure['expected']} "
                    f"got={failure['prediction']}"
                )

                ranked = sorted(
                    failure["probabilities"].items(),
                    key=lambda item: item[1],
                    reverse=True,
                )

                for label, probability in ranked:
                    print(
                        f"    {label:<25} "
                        f"{probability:.4f}"
                    )

        else:
            print()
            print("Choice failures: none")

        print()
        print("Score cases:")

        for score in result["score_results"]:

            print(
                f"  {score['id']:<22}"
                f"expected={score['expected']:.2f}  "
                f"predicted={score['prediction']:.3f}  "
                f"error={score['error']:.3f}"
            )


def save_results(results):
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        RESULTS_DIR
        / "template_ablation.json"
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"Saved: {output}")


def main():
    cases = load_cases()

    choice_count = sum(
        1 for case in cases
        if case["type"] == "choice"
    )

    score_count = sum(
        1 for case in cases
        if case["type"] == "score"
    )

    print(
        f"Loaded {len(cases)} cases "
        f"({choice_count} Choice, "
        f"{score_count} Score)."
    )

    print(
        "Noul cases excluded from template ablation."
    )

    print()

    engine = OpenDecisionEngine()

    results = []

    for index, profile in enumerate(
        PROFILES,
        start=1,
    ):
        print(
            f"[{index}/{len(PROFILES)}] "
            f"{profile.name}"
        )

        result = run_profile(
            engine,
            cases,
            profile,
        )

        results.append(result)

    print_summary(results)
    print_details(results)
    save_results(results)


if __name__ == "__main__":
    main()