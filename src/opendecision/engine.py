import json
from typing import Any, Mapping, Sequence
import math
import torch
from transformers import pipeline


DEFAULT_MODEL = "MoritzLaurer/ModernBERT-large-zeroshot-v2.0"
DEFAULT_BATCH_SIZE = 8


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
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")

        if device is None:
            device = _best_device()

        print(f"Loading {model}")
        print(f"Device: {device}")

        self.classifier = pipeline(
            "zero-shot-classification",
            model=model,
            device=device,
        )
        self.batch_size = batch_size

    def _inference_batch_size(self, item_count: int) -> int:
        return min(self.batch_size, item_count)

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
            batch_size=self._inference_batch_size(len(candidates)),
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
            batch_size=self._inference_batch_size(len(criteria)),
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

    def _choice_profile(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Mapping[str, str | None],
        premise_mode: str,
        candidate_mode: str,
        hypothesis_mode: str,
    ) -> tuple[str, dict[str, float]]:

        state_text = _serialize_state(state)

        if premise_mode == "state":
            sequence = state_text
        elif premise_mode == "state_question":
            sequence = f"{state_text}\n\nQuestion: {instructions}"
        else:
            raise ValueError(f"Unknown premise mode: {premise_mode}")

        rendered_candidates = []
        reverse_mapping = {}

        for name, description in criteria.items():
            natural_name = name.replace("_", " ")

            if candidate_mode == "description":
                rendered = description or natural_name
            elif candidate_mode == "label":
                rendered = natural_name
            elif candidate_mode == "label_description":
                rendered = (
                    f"{natural_name}: {description}"
                    if description
                    else natural_name
                )
            else:
                raise ValueError(
                    f"Unknown candidate mode: {candidate_mode}"
                )

            if rendered in reverse_mapping:
                rendered = f"{natural_name}: {rendered}"

            rendered_candidates.append(rendered)
            reverse_mapping[rendered] = name

        kwargs = {
            "candidate_labels": rendered_candidates,
            "multi_label": False,
        }

        if hypothesis_mode == "question":
            kwargs["hypothesis_template"] = (
                f'The answer to the question '
                f'"{instructions}" is {{}}.'
            )
        elif hypothesis_mode != "default":
            raise ValueError(
                f"Unknown hypothesis mode: {hypothesis_mode}"
            )

        raw = self.classifier(
            sequence,
            batch_size=self._inference_batch_size(len(criteria)),
            **kwargs,
        )

        probabilities = {
            reverse_mapping[label]: float(score)
            for label, score in zip(
                raw["labels"],
                raw["scores"],
            )
        }

        probabilities = {
            name: probabilities[name]
            for name in criteria
        }

        winner = max(probabilities, key=probabilities.get)

        return winner, probabilities

    def choice(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Mapping[str, str | None],
    ) -> dict:
        if len(criteria) < 2:
            raise ValueError("Choice requires at least two candidates.")

        # Compiler A
        answer_a, probabilities_a = self._choice_profile(
            state=state,
            instructions=instructions,
            criteria=criteria,
            premise_mode="state",
            candidate_mode="description",
            hypothesis_mode="question",
        )

        # Compiler B
        answer_b, probabilities_b = self._choice_profile(
            state=state,
            instructions=instructions,
            criteria=criteria,
            premise_mode="state",
            candidate_mode="label_description",
            hypothesis_mode="default",
        )

        if answer_a == answer_b:
            winner = answer_a

            probabilities = {
                name: (
                    probabilities_a[name]
                    + probabilities_b[name]
                ) / 2.0
                for name in criteria
            }

        else:
            disputed = {
                name: criteria[name]
                for name in criteria
                if name in {answer_a, answer_b}
            }

            # Frozen adjudicator selected on development data:
            # state + question / labels only / default hypothesis
            winner, _ = self._choice_profile(
                state=state,
                instructions=instructions,
                criteria=disputed,
                premise_mode="state_question",
                candidate_mode="label",
                hypothesis_mode="default",
            )

            probabilities = (
                probabilities_a
                if winner == answer_a
                else probabilities_b
            )

        return {
            "type": "choice",
            "choice": winner,
            "probabilities": probabilities,
            "confidence": _distribution_confidence(
                probabilities
            ),
        }

    def choice_fast(
        self,
        *,
        state: Any,
        instructions: str,
        criteria: Mapping[str, str | None],
    ) -> dict:
        """Return one zero-shot choice profile without cross-profile arbitration.

        Use this when latency matters more than the additional robustness of
        :meth:`choice`, such as a real-time control loop with fixed actions.
        """
        if len(criteria) < 2:
            raise ValueError("Choice requires at least two candidates.")

        winner, probabilities = self._choice_profile(
            state=state,
            instructions=instructions,
            criteria=criteria,
            premise_mode="state",
            candidate_mode="label_description",
            hypothesis_mode="default",
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
