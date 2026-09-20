import pytest

from opendecision.rules import evaluate_rule, relation_status


def test_relation_status_mapping():
    assert relation_status("supports") == "established"
    assert relation_status("contradicts") == "refuted"
    assert relation_status("conflicted") == "conflicted"
    assert relation_status("unknown") == "unknown"


def test_all_rule_preserves_trace():
    result = evaluate_rule(
        {"all": ["identity_verified", "documents_present"]},
        {
            "identity_verified": "established",
            "documents_present": "unknown",
        },
    )

    assert result["status"] == "unknown"
    assert [child["fact"] for child in result["children"]] == [
        "identity_verified",
        "documents_present",
    ]


def test_any_rule_is_refuted_only_when_every_input_is_refuted():
    assert evaluate_rule(
        {"any": ["a", "b"]},
        {"a": "refuted", "b": "unknown"},
    )["status"] == "unknown"

    assert evaluate_rule(
        {"any": ["a", "b"]},
        {"a": "refuted", "b": "refuted"},
    )["status"] == "refuted"


def test_not_swaps_support_and_refutation():
    assert evaluate_rule(
        {"not": "document_missing"},
        {"document_missing": "established"},
    )["status"] == "refuted"


def test_unknown_fact_is_rejected():
    with pytest.raises(ValueError, match="Unknown fact"):
        evaluate_rule("missing", {})
