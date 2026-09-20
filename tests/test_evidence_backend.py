from opendecision.engine import OpenDecisionEngine
from opendecision.evidence import NliEvidenceBackend


class RecordingEvidenceBackend:
    def __init__(self):
        self.calls = []

    def relations(self, **kwargs):
        self.calls.append(("relations", kwargs))
        return [{"relation": "supports"}]

    def relation(self, **kwargs):
        self.calls.append(("relation", kwargs))
        return {"relation": "unknown"}

    def rank_evidence(self, **kwargs):
        self.calls.append(("rank_evidence", kwargs))
        return [{"id": "policy-7"}]


def engine_with_backend(backend):
    engine = OpenDecisionEngine.__new__(OpenDecisionEngine)
    engine.evidence_backend = backend
    return engine


def test_engine_delegates_relation_to_replaceable_backend():
    backend = RecordingEvidenceBackend()
    engine = engine_with_backend(backend)

    result = engine.relation(
        state="A supplier certificate expired on 2026-04-01.",
        proposition="The certificate is expired.",
        contradiction="The certificate is current.",
    )

    assert result == {"relation": "unknown"}
    assert backend.calls[0][0] == "relation"
    assert backend.calls[0][1]["proposition"] == (
        "The certificate is expired."
    )


def test_engine_passes_developer_anchors_to_backend():
    backend = RecordingEvidenceBackend()
    engine = engine_with_backend(backend)

    result = engine.rank_evidence(
        evidence=[{"id": "policy-7", "text": "Policy text"}],
        proposition="Which policy governs order PO-2026-104?",
        anchors=["PO-2026-104", "政策-7"],
        top_k=1,
    )

    assert result == [{"id": "policy-7"}]
    assert backend.calls[0][1]["anchors"] == [
        "PO-2026-104",
        "政策-7",
    ]


def test_automatic_anchors_are_numeric_not_currency_specific():
    anchors = NliEvidenceBackend._automatic_anchors(
        "Compare €2.503,50, ₹84,000, and the 2026-09-20 deadline."
    )

    assert anchors == {"2.503,50", "84,000", "2026-09-20"}


def test_anchor_matching_is_unicode_case_insensitive():
    matches = NliEvidenceBackend._anchor_matches(
        "Référence 政策-7 applies to this request.",
        {"référence", "政策-7"},
    )

    assert matches == 2
