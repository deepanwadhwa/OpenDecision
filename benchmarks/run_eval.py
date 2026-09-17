import json
from pathlib import Path

from opendecision.engine import OpenDecisionEngine


DATASET = Path(__file__).parent / "cases.jsonl"


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


def evaluate_choice(engine, case):
    result = engine.choice(
        state=case["state"],
        instructions=case["instructions"],
        criteria=case["criteria"],
    )

    prediction = result["choice"]
    expected = case["expected"]

    return {
        "correct": prediction == expected,
        "prediction": prediction,
        "expected": expected,
        "result": result,
    }


def evaluate_noul(engine, case):
    result = engine.noul(
        state=case["state"],
        instructions=case["instructions"],
        criteria=case.get("criteria"),
    )

    probability = result["noul"]
    prediction = probability >= 0.5
    expected = case["expected"]

    return {
        "correct": prediction == expected,
        "prediction": prediction,
        "expected": expected,
        "probability": probability,
        "result": result,
    }


def evaluate_score(engine, case):
    result = engine.score(
        state=case["state"],
        instructions=case["instructions"],
        criteria=case["criteria"],
    )

    prediction = result["score"]
    expected = float(case["expected"])

    error = abs(prediction - expected)

    return {
        "error": error,
        "prediction": prediction,
        "expected": expected,
        "result": result,
    }


def main():
    cases = load_cases()

    print(f"Loaded {len(cases)} benchmark cases.")
    print()

    engine = OpenDecisionEngine()

    choice_total = 0
    choice_correct = 0

    noul_total = 0
    noul_correct = 0

    score_errors = []

    failures = []

    for case in cases:
        case_type = case["type"]

        if case_type == "choice":
            outcome = evaluate_choice(engine, case)

            choice_total += 1
            choice_correct += int(outcome["correct"])

            if not outcome["correct"]:
                failures.append((case, outcome))

        elif case_type == "noul":
            outcome = evaluate_noul(engine, case)

            noul_total += 1
            noul_correct += int(outcome["correct"])

            if not outcome["correct"]:
                failures.append((case, outcome))

        elif case_type == "score":
            outcome = evaluate_score(engine, case)
            score_errors.append(outcome["error"])

        else:
            raise ValueError(
                f"Unknown case type: {case_type}"
            )

    print()
    print("OpenDecision M4 Evaluation")
    print("=" * 40)

    if choice_total:
        accuracy = choice_correct / choice_total

        print(
            f"Choice accuracy: "
            f"{choice_correct}/{choice_total} "
            f"= {accuracy:.1%}"
        )

    if noul_total:
        accuracy = noul_correct / noul_total

        print(
            f"Noul accuracy:   "
            f"{noul_correct}/{noul_total} "
            f"= {accuracy:.1%}"
        )

    if score_errors:
        mae = sum(score_errors) / len(score_errors)

        print(
            f"Score MAE:       "
            f"{mae:.3f}"
        )

    print(f"Total cases:     {len(cases)}")
    print(f"Failures:        {len(failures)}")

    if failures:
        print()
        print("Failures")
        print("-" * 40)

        for case, outcome in failures:
            print()
            print(f"ID:       {case['id']}")
            print(f"Expected: {outcome['expected']}")
            print(f"Got:      {outcome['prediction']}")

            if "probability" in outcome:
                print(
                    f"P(true):  "
                    f"{outcome['probability']:.4f}"
                )

            probabilities = outcome["result"].get(
                "probabilities"
            )

            if probabilities:
                print("Probabilities:")

                for label, probability in sorted(
                    probabilities.items(),
                    key=lambda item: item[1],
                    reverse=True,
                ):
                    print(
                        f"  {label:<25} "
                        f"{probability:.4f}"
                    )


if __name__ == "__main__":
    main()