from __future__ import annotations

from collections.abc import Mapping
from typing import Any


VALID_STATUSES = {
    "established",
    "refuted",
    "conflicted",
    "unknown",
}


def relation_status(relation: str) -> str:
    mapping = {
        "supports": "established",
        "contradicts": "refuted",
        "conflicted": "conflicted",
        "unknown": "unknown",
    }

    try:
        return mapping[relation]
    except KeyError as error:
        raise ValueError(f"Unknown evidence relation: {relation!r}.") from error


def _truth_bits(status: str) -> tuple[bool, bool]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown decision status: {status!r}.")

    return {
        "established": (True, False),
        "refuted": (False, True),
        "conflicted": (True, True),
        "unknown": (False, False),
    }[status]


def _status(supported: bool, refuted: bool) -> str:
    return {
        (True, False): "established",
        (False, True): "refuted",
        (True, True): "conflicted",
        (False, False): "unknown",
    }[(supported, refuted)]


def evaluate_rule(
    rule: str | Mapping[str, Any],
    facts: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate a small auditable rule tree with four-valued logic.

    A string is a fact reference. Mappings contain exactly one of ``all``,
    ``any``, or ``not``. The returned trace preserves every input used to
    reach the result.
    """
    if isinstance(rule, str):
        if rule not in facts:
            raise ValueError(f"Unknown fact referenced by rule: {rule!r}.")

        status = facts[rule]
        _truth_bits(status)
        return {
            "op": "fact",
            "fact": rule,
            "status": status,
        }

    operators = [key for key in ("all", "any", "not") if key in rule]

    if len(operators) != 1:
        raise ValueError("A rule must contain exactly one operator.")

    operator = operators[0]

    if operator == "not":
        child = evaluate_rule(rule[operator], facts)
        supported, refuted = _truth_bits(child["status"])
        return {
            "op": "not",
            "status": _status(refuted, supported),
            "children": [child],
        }

    operands = rule[operator]

    if not isinstance(operands, list) or not operands:
        raise ValueError(f"{operator!r} requires a non-empty list.")

    children = [evaluate_rule(operand, facts) for operand in operands]
    bits = [_truth_bits(child["status"]) for child in children]

    if operator == "all":
        supported = all(bit[0] for bit in bits)
        refuted = any(bit[1] for bit in bits)
    else:
        supported = any(bit[0] for bit in bits)
        refuted = all(bit[1] for bit in bits)

    return {
        "op": operator,
        "status": _status(supported, refuted),
        "children": children,
    }
