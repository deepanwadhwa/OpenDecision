import json
from typing import Any, Mapping, Sequence
import math
import torch
from transformers import pipeline


DEFAULT_MODEL = "MoritzLaurer/ModernBERT-large-zeroshot-v2.0"


def _best_device():
    if torch.cuda.is_available():
        return 0

    if torch.backends.mps.is_available():
        return "mps"

    return -1


def _serialize_state(state: Any) -> str:
    """
    Convert OpenDecision state into deterministic text.

    Strings are preserved.
    Dicts/lists are serialized as stable JSON.
    """
    if isinstance(state, str):
        return state

    return json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _make_sequence(state: Any, instructions: str) -> str:
    state_text = _serialize_state(state)

    return (
        f"State:\n{state_text}\n\n"
        f"Question:\n{instructions}"
    )




def _distribution_confidence(
    probabilities: dict[str, float],
) -> float:
    """
    Confidence derived from normalized entropy.

    1.0 = probability mass concentrated on one option
    0.0 = uniform distribution

    This is OpenDecision's confidence definition, not TypeSafe's.
    """
    values = list(probabilities.values())

    if len(values) <= 1:
        return 1.0

    entropy = -sum(
        p * math.log(p)
        for p in values
        if p > 0.0
    )

    max_entropy = math.log(len(values))

    confidence = 1.0 - (entropy / max_entropy)

    return float(max(0.0, min(1.0, confidence)))


class OpenDecisionEngine:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device=None,
    ):
        if device is None:
            device = _best_device()

        print(f"Loading {model}")
        print(f"Device: {device}")

        self.classifier = pipeline(
            "zero-shot-classification",
            model=model,
            device=device,
        )

    def _classify(
        self,
        *,
        state: Any,
        instructions: str,
        candidates: Mapping[str, str | None],
    ) -> dict[str, float]:
        """
        Internal primitive.

        Takes arbitrary named candidates and returns:

            {
                candidate_name: probability,
                ...
            }
        """

        sequence = _make_sequence(state, instructions)

        rendered_candidates = {}
        reverse_mapping = {}

        for name, description in candidates.items():

            natural_name = name.replace("_", " ")

            # If a semantic description exists, show only that to the model.
            # Keep the machine-readable name only for mapping the result back.
            if description:
                rendered = description
            else:
                rendered = natural_name

            # Avoid collisions if two classes have identical descriptions.
            if rendered in reverse_mapping:
                rendered = f"{natural_name}: {rendered}"

            rendered_candidates[name] = rendered
            reverse_mapping[rendered] = name

        raw = self.classifier(
        sequence,
        candidate_labels=list(rendered_candidates.values()),
        multi_label=False,
    )

        probabilities = {}

        for rendered_label, score in zip(
            raw["labels"],
            raw["scores"],
        ):
            original_name = reverse_mapping[rendered_label]
            probabilities[original_name] = float(score)

        # Return candidates in the user's original order.
        return {
            name: probabilities[name]
            for name in candidates
        }

    def _classify_score(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Sequence[str],
    ) -> dict[str, float]:

        premise = _serialize_state(state)

        description_to_index = {
            description: str(index)
            for index, description in enumerate(criteria)
        }

        hypothesis_template = (
            f'The answer to the question "{instructions}" is {{}}.'
        )

        raw = self.classifier(
            premise,
            candidate_labels=list(criteria),
            multi_label=False,
            hypothesis_template=hypothesis_template,
        )

        probabilities = {}

        for description, score in zip(
            raw["labels"],
            raw["scores"],
        ):
            index = description_to_index[description]
            probabilities[index] = float(score)

        return {
            str(index): probabilities[str(index)]
            for index in range(len(criteria))
        }
    # ---------------------------------------------------------
    # CHOICE
    # ---------------------------------------------------------

    def choice(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Mapping[str, str | None],
    ) -> dict:
        if len(criteria) < 2:
            raise ValueError("Choice requires at least two candidates.")

        probabilities = self._classify(
            state=state,
            instructions=instructions,
            candidates=criteria,
        )

        winner = max(
            probabilities,
            key=probabilities.get,
        )

        return {
        "type": "choice",
        "choice": winner,
        "probabilities": probabilities,
        "confidence": _distribution_confidence(probabilities),
    }

    # ---------------------------------------------------------
    # NOUL
    # ---------------------------------------------------------

    def _entailment_probability(
        self,
        *,
        state: Any,
        hypothesis: str,
    ) -> float:

        premise = _serialize_state(state)

        tokenizer = self.classifier.tokenizer
        model = self.classifier.model

        inputs = tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=8192,
        )

        device = next(model.parameters()).device

        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }

        with torch.inference_mode():
            logits = model(**inputs).logits[0]

        probabilities = torch.softmax(
            logits.float(),
            dim=-1,
        )

        entailment_id = model.config.label2id["entailment"]

        return float(probabilities[entailment_id])

    def _entailment_logit(
        self,
        *,
        state: Any,
        hypothesis: str,
    ) -> float:

        premise = _serialize_state(state)

        tokenizer = self.classifier.tokenizer
        model = self.classifier.model

        inputs = tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=8192,
        )

        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = model(**inputs).logits[0]

        entailment_id = model.config.label2id["entailment"]

        return float(logits[entailment_id])

    def noul(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Mapping[str, str] | None = None,
    ) -> dict:

        # Simple predicate:
        # state -> does it entail the supplied statement?
        if criteria is None:
            probability = self._entailment_probability(
                state=state,
                hypothesis=instructions,
            )

            return {
                "type": "noul",
                "noul": probability,
            }

        # Explicit true/false semantic definitions:
        true_hypothesis = criteria["true"]
        false_hypothesis = criteria["false"]

        true_logit = self._entailment_logit(
            state=state,
            hypothesis=true_hypothesis,
        )

        false_logit = self._entailment_logit(
            state=state,
            hypothesis=false_hypothesis,
        )

        logits = torch.tensor(
            [true_logit, false_logit],
            dtype=torch.float32,
        )

        probabilities = torch.softmax(logits, dim=0)

        return {
            "type": "noul",
            "noul": float(probabilities[0]),
        }
    # ---------------------------------------------------------
    # SCORE
    # ---------------------------------------------------------

    def score(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Sequence[str],
    ) -> dict:
        if len(criteria) < 2:
            raise ValueError("Score requires at least two levels.")

        if len(set(criteria)) != len(criteria):
            raise ValueError("Score criteria must be unique.")

        probabilities = self._classify_score(
            state=state,
            instructions=instructions,
            criteria=criteria,
        )
        weighted_score = sum(
            int(index) * probability
            for index, probability in probabilities.items()
        )

        legend = {
            str(index): description
            for index, description in enumerate(criteria)
        }

        return {
        "type": "score",
        "score": weighted_score,
        "legend": legend,
        "probabilities": probabilities,
        "confidence": _distribution_confidence(probabilities),
    }