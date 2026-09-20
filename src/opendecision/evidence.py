from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

import torch


Serializer = Callable[[Any], str]


class EvidenceBackend(Protocol):
    """Replaceable backend contract used by :class:`OpenDecisionEngine`."""

    def relations(
        self,
        *,
        items: Sequence[Mapping[str, Any]],
        threshold: float = 0.5,
    ) -> list[dict]: ...

    def relation(
        self,
        *,
        state: Any,
        proposition: str,
        contradiction: str,
        threshold: float = 0.5,
    ) -> dict: ...

    def rank_evidence(
        self,
        *,
        evidence: Sequence[Mapping[str, Any]],
        proposition: str,
        contradiction: str | None = None,
        top_k: int | None = None,
        anchors: Sequence[str] | None = None,
    ) -> list[dict]: ...


class NliEvidenceBackend:
    """Domain-neutral evidence relation and relevance operations.

    The backend adapts to either a native three-way NLI model or a binary
    entailment model. It owns no domain ontology or decision policy; callers
    provide propositions, explicit opposites, evidence units, and optional
    exact anchors.
    """

    def __init__(
        self,
        *,
        classifier: Any,
        batch_size: int,
        serializer: Serializer,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")

        self.classifier = classifier
        self.batch_size = batch_size
        self.serialize = serializer

    def _has_native_nli(self) -> bool:
        label_names = {
            str(label).lower()
            for label in self.classifier.model.config.label2id
        }
        return {
            "entailment",
            "contradiction",
            "neutral",
        }.issubset(label_names)

    def _max_length(self) -> int:
        tokenizer = self.classifier.tokenizer
        model = self.classifier.model
        model_limit = int(
            getattr(model.config, "max_position_embeddings", 512)
        )
        tokenizer_limit = int(
            getattr(tokenizer, "model_max_length", model_limit)
        )
        return min(model_limit, tokenizer_limit)

    def _tokenize_pairs(
        self,
        pairs: Sequence[tuple[Any, str]],
    ) -> dict[str, torch.Tensor]:
        inputs = self.classifier.tokenizer(
            [self.serialize(state) for state, _ in pairs],
            [hypothesis for _, hypothesis in pairs],
            return_tensors="pt",
            padding=True,
            truncation="only_first",
            max_length=self._max_length(),
        )
        device = next(self.classifier.model.parameters()).device
        return {
            key: value.to(device)
            for key, value in inputs.items()
        }

    def _entailment_probabilities_batch(
        self,
        pairs: Sequence[tuple[Any, str]],
    ) -> list[float]:
        """Score premise/hypothesis pairs independently."""
        if not pairs:
            return []

        model = self.classifier.model
        entailment_id = model.config.label2id["entailment"]
        probabilities: list[float] = []

        for start in range(0, len(pairs), self.batch_size):
            batch = pairs[start : start + self.batch_size]

            with torch.inference_mode():
                logits = model(**self._tokenize_pairs(batch)).logits

            batch_probabilities = torch.softmax(
                logits.float(),
                dim=-1,
            )[:, entailment_id]
            probabilities.extend(
                float(probability)
                for probability in batch_probabilities.cpu()
            )

        return probabilities

    def _nli_probabilities_batch(
        self,
        pairs: Sequence[tuple[Any, str]],
    ) -> list[dict[str, float]]:
        """Return native NLI distributions for premise/hypothesis pairs."""
        if not pairs:
            return []

        model = self.classifier.model
        label2id = {
            str(label).lower(): int(index)
            for label, index in model.config.label2id.items()
        }
        required = {"entailment", "contradiction", "neutral"}

        if not required.issubset(label2id):
            raise ValueError(
                "The configured model does not expose native three-way NLI "
                "labels: entailment, contradiction, and neutral."
            )

        distributions: list[dict[str, float]] = []

        for start in range(0, len(pairs), self.batch_size):
            batch = pairs[start : start + self.batch_size]

            with torch.inference_mode():
                logits = model(**self._tokenize_pairs(batch)).logits

            probabilities = torch.softmax(logits.float(), dim=-1).cpu()

            for row in probabilities:
                distributions.append(
                    {
                        label: float(row[index])
                        for label, index in label2id.items()
                        if label in required
                    }
                )

        return distributions

    @staticmethod
    def _relation_from_binary_scores(
        support: float,
        contradict: float,
        threshold: float,
    ) -> str:
        support_present = support >= threshold
        contradiction_present = contradict >= threshold

        if support_present and contradiction_present:
            return "conflicted"
        if support_present:
            return "supports"
        if contradiction_present:
            return "contradicts"
        return "unknown"

    def relations(
        self,
        *,
        items: Sequence[Mapping[str, Any]],
        threshold: float = 0.5,
    ) -> list[dict]:
        """Relate evidence to propositions using explicit opposites."""
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be between 0 and 1.")

        native_nli = self._has_native_nli()
        pairs: list[tuple[Any, str]] = []

        for item in items:
            missing = {
                key
                for key in ("state", "proposition", "contradiction")
                if key not in item
            }
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ValueError(
                    f"Relation item is missing: {missing_text}."
                )

            pairs.append((item["state"], str(item["proposition"])))

            if not native_nli:
                pairs.append(
                    (item["state"], str(item["contradiction"]))
                )

        if native_nli:
            distributions = self._nli_probabilities_batch(pairs)
            label_to_relation = {
                "entailment": "supports",
                "contradiction": "contradicts",
                "neutral": "unknown",
            }
            results = []

            for distribution in distributions:
                winner = max(distribution, key=distribution.get)
                results.append(
                    {
                        "type": "relation",
                        "relation": label_to_relation[winner],
                        "scores": {
                            "supports": distribution["entailment"],
                            "contradicts": distribution["contradiction"],
                            "unknown": distribution["neutral"],
                        },
                        "backend": "native_nli",
                    }
                )

            return results

        entailment = self._entailment_probabilities_batch(pairs)
        results = []

        for index in range(len(items)):
            support = entailment[index * 2]
            contradict = entailment[index * 2 + 1]
            results.append(
                {
                    "type": "relation",
                    "relation": self._relation_from_binary_scores(
                        support,
                        contradict,
                        threshold,
                    ),
                    "scores": {
                        "supports": support,
                        "contradicts": contradict,
                    },
                    "threshold": threshold,
                    "backend": "explicit_opposite",
                }
            )

        return results

    def relation(
        self,
        *,
        state: Any,
        proposition: str,
        contradiction: str,
        threshold: float = 0.5,
    ) -> dict:
        return self.relations(
            items=[
                {
                    "state": state,
                    "proposition": proposition,
                    "contradiction": contradiction,
                }
            ],
            threshold=threshold,
        )[0]

    @staticmethod
    def _automatic_anchors(proposition: str) -> set[str]:
        """Extract exact numeric anchors without assuming a currency/domain."""
        return {
            anchor.casefold()
            for anchor in re.findall(
                r"(?<!\w)\d(?:[\d,._:/-]*\d)?(?!\w)",
                proposition,
            )
        }

    def rank_evidence(
        self,
        *,
        evidence: Sequence[Mapping[str, Any]],
        proposition: str,
        contradiction: str | None = None,
        top_k: int | None = None,
        anchors: Sequence[str] | None = None,
    ) -> list[dict]:
        """Rank evidence units by semantic relevance and exact anchors.

        Native three-way NLI uses ``1 - P(neutral)`` so both supporting and
        contradicting passages are relevant. Callers may provide exact anchors
        such as identifiers, dates, amounts, citations, or domain terms.
        Numeric anchors are also discovered automatically from the proposition.
        """
        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be at least 1.")

        native_nli = self._has_native_nli()
        units = list(evidence)
        exact_anchors = self._automatic_anchors(proposition)
        exact_anchors.update(
            str(anchor).casefold()
            for anchor in anchors or ()
            if str(anchor)
        )

        for unit in units:
            if "id" not in unit or "text" not in unit:
                raise ValueError(
                    "Each evidence unit must contain id and text."
                )

        pairs = [
            (unit["text"], proposition)
            for unit in units
        ]

        if native_nli:
            distributions = self._nli_probabilities_batch(pairs)
            rows = []

            for unit, distribution in zip(units, distributions):
                winner = max(distribution, key=distribution.get)
                rows.append(
                    {
                        "id": unit["id"],
                        "text": unit["text"],
                        "relevance": 1.0 - distribution["neutral"],
                        "relation": {
                            "entailment": "supports",
                            "contradiction": "contradicts",
                            "neutral": "unknown",
                        }[winner],
                        "scores": distribution,
                        "anchor_matches": self._anchor_matches(
                            unit["text"],
                            exact_anchors,
                        ),
                    }
                )
        else:
            if contradiction is None:
                raise ValueError(
                    "Binary NLI backends require an explicit contradiction "
                    "for evidence ranking."
                )

            binary_pairs = []
            for unit in units:
                binary_pairs.append((unit["text"], proposition))
                binary_pairs.append((unit["text"], contradiction))

            probabilities = self._entailment_probabilities_batch(
                binary_pairs
            )
            rows = []

            for index, unit in enumerate(units):
                support = probabilities[index * 2]
                contradict = probabilities[index * 2 + 1]
                rows.append(
                    {
                        "id": unit["id"],
                        "text": unit["text"],
                        "relevance": max(support, contradict),
                        "relation": (
                            "supports"
                            if support >= contradict
                            else "contradicts"
                        ),
                        "scores": {
                            "entailment": support,
                            "contradiction": contradict,
                        },
                        "anchor_matches": self._anchor_matches(
                            unit["text"],
                            exact_anchors,
                        ),
                    }
                )

        rows.sort(
            key=lambda row: (
                row["anchor_matches"],
                row["relevance"],
            ),
            reverse=True,
        )
        return rows[:top_k] if top_k is not None else rows

    @staticmethod
    def _anchor_matches(text: Any, anchors: set[str]) -> int:
        normalized_text = str(text).casefold()
        return sum(anchor in normalized_text for anchor in anchors)
