from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from opendecision.engine import OpenDecisionEngine


DEFAULT_CHUNK_TOKENS = 384
DEFAULT_TOP_K = 4


def _serialize_document(document: Any) -> str:
    if isinstance(document, str):
        text = document

        # Some copied/exported documents contain escaped line breaks instead
        # of real ones. Only repair that shape when the text is effectively
        # one physical line, so ordinary source code and JSON are untouched.
        if text.count("\n") < 2 and text.count("\\n") >= 2:
            return text.replace("\\n", "\n")

        return text

    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        default=str,
    )


def _heading(line: str) -> str | None:
    stripped = line.strip()

    wiki = re.fullmatch(r"={2,}\s*(.*?)\s*={2,}", stripped)
    if wiki:
        return wiki.group(1).strip()

    markdown = re.fullmatch(r"#{1,6}\s+(.+?)\s*#*", stripped)
    if markdown:
        return markdown.group(1).strip()

    return None


def _structural_blocks(text: str) -> list[tuple[str | None, str]]:
    """Split text using common headings and paragraph boundaries."""
    lines = text.splitlines()
    blocks: list[tuple[str | None, str]] = []
    title: str | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal body
        content = "\n".join(body).strip()
        if content:
            blocks.append((title, content))
        body = []

    index = 0
    while index < len(lines):
        line = lines[index]
        detected = _heading(line)

        # Also recognize the common plain-text shape:
        # ======== / SECTION TITLE / ========
        if (
            detected is None
            and re.fullmatch(r"\s*[=_-]{6,}\s*", line)
            and index + 2 < len(lines)
            and lines[index + 1].strip()
            and re.fullmatch(r"\s*[=_-]{6,}\s*", lines[index + 2])
        ):
            flush()
            title = lines[index + 1].strip()
            index += 3
            continue

        if detected is not None:
            flush()
            title = detected
        elif not line.strip():
            flush()
        else:
            body.append(line)

        index += 1

    flush()
    return blocks or [(None, text)]


def _token_ids(tokenizer: Any, text: str) -> list[int]:
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
    )
    return list(encoded["input_ids"])


def _split_token_ids(
    tokenizer: Any,
    text: str,
    max_tokens: int,
) -> list[str]:
    token_ids = _token_ids(tokenizer, text)
    if len(token_ids) <= max_tokens:
        return [text]

    return [
        tokenizer.decode(
            token_ids[start : start + max_tokens],
            skip_special_tokens=True,
        ).strip()
        for start in range(0, len(token_ids), max_tokens)
    ]


def split_document(
    document: Any,
    *,
    tokenizer: Any,
    max_tokens: int = DEFAULT_CHUNK_TOKENS,
) -> list[dict[str, str]]:
    """Turn arbitrary text or structured state into bounded evidence units.

    The splitter contains no domain vocabulary. It preserves a small document
    as one unit, otherwise uses common heading/paragraph structure and finally
    a tokenizer-sized fallback.
    """
    if max_tokens < 32:
        raise ValueError("max_tokens must be at least 32.")

    text = _serialize_document(document).strip()
    if not text:
        raise ValueError("document must not be empty.")

    if len(_token_ids(tokenizer, text)) <= max_tokens:
        return [{"id": "document", "text": text}]

    units: list[dict[str, str]] = []

    for title, block in _structural_blocks(text):
        rendered = f"{title}\n\n{block}" if title else block
        pieces = _split_token_ids(tokenizer, rendered, max_tokens)

        for piece in pieces:
            if not piece:
                continue
            units.append(
                {
                    "id": f"section-{len(units) + 1:03d}",
                    "text": piece,
                }
            )

    return units


def compile_boolean_question(question: str) -> tuple[str, str]:
    """Compile any yes/no question with one transparent generic template."""
    normalized = " ".join(question.split())
    if not normalized:
        raise ValueError("question must not be empty.")

    return (
        f'The answer to the question "{normalized}" is yes.',
        f'The answer to the question "{normalized}" is no.',
    )


class DocumentDecisionService:
    """Generic retrieval and decision orchestration for arbitrary documents."""

    def __init__(
        self,
        engine: OpenDecisionEngine,
        *,
        top_k: int = DEFAULT_TOP_K,
        chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        self.engine = engine
        self.top_k = top_k
        self.chunk_tokens = chunk_tokens

    def chunks(self, document: Any) -> list[dict[str, str]]:
        return split_document(
            document,
            tokenizer=self.engine.classifier.tokenizer,
            max_tokens=self.chunk_tokens,
        )

    def _evidence(
        self,
        chunks: Sequence[Mapping[str, str]],
        *,
        proposition: str,
        contradiction: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        if len(chunks) <= self.top_k:
            rows = [
                {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "relevance": 1.0,
                }
                for chunk in chunks
            ]
        else:
            rows = self.engine.rank_evidence(
                evidence=chunks,
                proposition=proposition,
                contradiction=contradiction,
                top_k=self.top_k,
            )

        evidence = "\n\n---\n\n".join(
            str(row["text"])
            for row in rows
        )
        citations = [
            {
                "id": str(row["id"]),
                "text": str(row["text"]),
                "relevance": float(row.get("relevance", 1.0)),
            }
            for row in rows
        ]
        return evidence, citations

    def noul(
        self,
        *,
        chunks: Sequence[Mapping[str, str]],
        instructions: str,
        criteria: Mapping[str, str] | None = None,
        mode: Literal["binary", "three_way", "both"] = "both",
    ) -> dict[str, Any]:
        if mode not in {"binary", "three_way", "both"}:
            raise ValueError(f"Unsupported Noul document mode: {mode!r}.")

        if criteria is None:
            proposition, contradiction = compile_boolean_question(instructions)
            compiler = "generic_yes_no"
        else:
            proposition = criteria["true"]
            contradiction = criteria["false"]
            compiler = "explicit_criteria"

        evidence, citations = self._evidence(
            chunks,
            proposition=proposition,
            contradiction=contradiction,
        )

        binary = None
        if mode in {"binary", "both"}:
            binary_result = self.engine.noul(
                state=evidence,
                instructions=instructions,
                criteria={
                    "true": proposition,
                    "false": contradiction,
                },
            )
            true_probability = float(binary_result["noul"])
            false_probability = 1.0 - true_probability
            binary = {
                "answer": true_probability >= 0.5,
                "probabilities": {
                    "true": true_probability,
                    "false": false_probability,
                },
                "confidence": max(true_probability, false_probability),
            }

        three_way = None
        if mode in {"three_way", "both"}:
            relation_result = self.engine.relation(
                state=evidence,
                proposition=proposition,
                contradiction=contradiction,
            )
            relation = relation_result["relation"]
            three_way = {
                "answer": {
                    "supports": True,
                    "contradicts": False,
                    "unknown": None,
                    "conflicted": None,
                }[relation],
                "relation": relation,
                "scores": relation_result["scores"],
            }

        if mode == "binary":
            answer = binary["answer"]
            status = "binary"
        elif mode == "three_way":
            answer = three_way["answer"]
            status = three_way["relation"]
        elif three_way["answer"] is None:
            answer = binary["answer"]
            status = "tentative"
        elif binary["answer"] == three_way["answer"]:
            answer = binary["answer"]
            status = "confirmed"
        else:
            answer = None
            status = "conflicted"

        return {
            "type": "document_noul",
            "mode": mode,
            "answer": answer,
            "status": status,
            "binary": binary,
            "three_way": three_way,
            "compiler": compiler,
            "compiled": {
                "proposition": proposition,
                "contradiction": contradiction,
            },
            "evidence": citations,
        }

    def relation(
        self,
        *,
        chunks: Sequence[Mapping[str, str]],
        proposition: str,
        contradiction: str,
        threshold: float,
    ) -> dict[str, Any]:
        evidence, citations = self._evidence(
            chunks,
            proposition=proposition,
            contradiction=contradiction,
        )
        result = self.engine.relation(
            state=evidence,
            proposition=proposition,
            contradiction=contradiction,
            threshold=threshold,
        )
        return {**result, "evidence": citations}

    def _candidate_evidence(
        self,
        chunks: Sequence[Mapping[str, str]],
        *,
        instructions: str,
        candidates: Sequence[str],
    ) -> tuple[str, list[dict[str, Any]]]:
        if len(chunks) <= self.top_k:
            return self._evidence(
                chunks,
                proposition=instructions,
                contradiction=f"The document is unrelated to: {instructions}",
            )

        selected: dict[str, dict[str, Any]] = {}
        per_candidate = max(1, self.top_k // len(candidates))

        for candidate in candidates:
            proposition = (
                f'The answer to the question "{instructions}" is '
                f'"{candidate}".'
            )
            opposite = (
                f'The answer to the question "{instructions}" is not '
                f'"{candidate}".'
            )
            ranked = self.engine.rank_evidence(
                evidence=chunks,
                proposition=proposition,
                contradiction=opposite,
                top_k=per_candidate,
            )
            for row in ranked:
                current = selected.get(str(row["id"]))
                if current is None or row["relevance"] > current["relevance"]:
                    selected[str(row["id"])] = row

        rows = sorted(
            selected.values(),
            key=lambda row: row["relevance"],
            reverse=True,
        )[: self.top_k]
        evidence = "\n\n---\n\n".join(str(row["text"]) for row in rows)
        citations = [
            {
                "id": str(row["id"]),
                "text": str(row["text"]),
                "relevance": float(row["relevance"]),
            }
            for row in rows
        ]
        return evidence, citations

    def choice(
        self,
        *,
        chunks: Sequence[Mapping[str, str]],
        instructions: str,
        criteria: Mapping[str, str | None],
    ) -> dict[str, Any]:
        rendered = [
            description or name.replace("_", " ")
            for name, description in criteria.items()
        ]
        evidence, citations = self._candidate_evidence(
            chunks,
            instructions=instructions,
            candidates=rendered,
        )
        result = self.engine.choice(
            state=evidence,
            instructions=instructions,
            criteria=criteria,
        )
        return {**result, "evidence": citations}

    def score(
        self,
        *,
        chunks: Sequence[Mapping[str, str]],
        instructions: str,
        criteria: Sequence[str],
    ) -> dict[str, Any]:
        evidence, citations = self._candidate_evidence(
            chunks,
            instructions=instructions,
            candidates=criteria,
        )
        result = self.engine.score(
            state=evidence,
            instructions=instructions,
            criteria=criteria,
        )
        return {**result, "evidence": citations}
