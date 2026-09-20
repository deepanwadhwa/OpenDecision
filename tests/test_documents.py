from opendecision.documents import (
    DocumentDecisionService,
    compile_boolean_question,
    split_document,
)


class WordTokenizer:
    def __init__(self):
        self.tokens = {}
        self.reverse = {}

    def __call__(self, text, **kwargs):
        ids = []
        for token in text.split():
            if token not in self.tokens:
                index = len(self.tokens) + 1
                self.tokens[token] = index
                self.reverse[index] = token
            ids.append(self.tokens[token])
        return {"input_ids": ids}

    def decode(self, token_ids, **kwargs):
        return " ".join(self.reverse[token_id] for token_id in token_ids)


class FakeClassifier:
    def __init__(self):
        self.tokenizer = WordTokenizer()


class FakeEngine:
    def __init__(self):
        self.classifier = FakeClassifier()
        self.relation_calls = []
        self.noul_calls = []

    def noul(self, **kwargs):
        self.noul_calls.append(kwargs)
        return {"type": "noul", "noul": 0.75}

    def relation(self, **kwargs):
        self.relation_calls.append(kwargs)
        return {
            "type": "relation",
            "relation": "supports",
            "scores": {
                "supports": 0.8,
                "contradicts": 0.1,
                "unknown": 0.1,
            },
        }


def test_compile_boolean_question_uses_one_generic_template():
    proposition, contradiction = compile_boolean_question(
        "  Is   collision coverage active?  "
    )

    assert proposition == (
        'The answer to the question "Is collision coverage active?" is yes.'
    )
    assert contradiction == (
        'The answer to the question "Is collision coverage active?" is no.'
    )


def test_small_structured_document_stays_in_one_evidence_unit():
    chunks = split_document(
        {"coverage": {"collision": True}, "deductible": 500},
        tokenizer=WordTokenizer(),
        max_tokens=32,
    )

    assert len(chunks) == 1
    assert chunks[0]["id"] == "document"
    assert '"collision": true' in chunks[0]["text"]


def test_long_text_uses_generic_headings_and_token_bounds():
    chunks = split_document(
        "== Coverage ==\\n" + "collision active words here " * 12 + "\\n\\n"
        "== Exclusions ==\\n" + "track driving excluded words here " * 12,
        tokenizer=WordTokenizer(),
        max_tokens=32,
    )

    assert len(chunks) >= 4
    assert all(chunk["text"] for chunk in chunks)


def test_document_noul_returns_compiler_and_provenance():
    engine = FakeEngine()
    service = DocumentDecisionService(engine)
    chunks = service.chunks({"collision": True})

    result = service.noul(
        chunks=chunks,
        instructions="Is collision coverage active?",
    )

    assert result["answer"] is True
    assert result["mode"] == "both"
    assert result["status"] == "confirmed"
    assert result["compiler"] == "generic_yes_no"
    assert result["compiled"]["proposition"].endswith("is yes.")
    assert result["evidence"][0]["id"] == "document"
    assert result["binary"] == {
        "answer": True,
        "probabilities": {"true": 0.75, "false": 0.25},
        "confidence": 0.75,
    }
    assert result["three_way"]["relation"] == "supports"
    assert engine.noul_calls[0]["criteria"] == {
        "true": result["compiled"]["proposition"],
        "false": result["compiled"]["contradiction"],
    }
    assert engine.relation_calls[0]["state"] == chunks[0]["text"]


def test_binary_mode_does_not_run_three_way_nli():
    engine = FakeEngine()
    service = DocumentDecisionService(engine)

    result = service.noul(
        chunks=service.chunks({"collision": True}),
        instructions="Is collision coverage active?",
        mode="binary",
    )

    assert result["answer"] is True
    assert result["status"] == "binary"
    assert result["three_way"] is None
    assert engine.relation_calls == []


def test_three_way_mode_does_not_run_binary_noul():
    engine = FakeEngine()
    service = DocumentDecisionService(engine)

    result = service.noul(
        chunks=service.chunks({"collision": True}),
        instructions="Is collision coverage active?",
        mode="three_way",
    )

    assert result["answer"] is True
    assert result["status"] == "supports"
    assert result["binary"] is None
    assert result["three_way"]["relation"] == "supports"
    assert engine.noul_calls == []


def test_both_mode_marks_binary_fallback_as_tentative():
    engine = FakeEngine()
    engine.relation = lambda **kwargs: {
        "type": "relation",
        "relation": "unknown",
        "scores": {
            "supports": 0.2,
            "contradicts": 0.2,
            "unknown": 0.6,
        },
    }
    service = DocumentDecisionService(engine)

    result = service.noul(
        chunks=service.chunks({"review": "not stated"}),
        instructions="Was the claim reviewed?",
    )

    assert result["answer"] is True
    assert result["status"] == "tentative"
    assert result["three_way"]["answer"] is None
