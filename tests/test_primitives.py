import pytest

from opendecision.engine import OpenDecisionEngine


@pytest.fixture(scope="session")
def engine():
    return OpenDecisionEngine()


def test_batch_size_must_be_positive():
    with pytest.raises(ValueError, match="batch_size"):
        OpenDecisionEngine(batch_size=0)


def test_choice(engine):
    result = engine.choice(
        state="My credit card was charged twice for the same subscription.",
        instructions="Which department should handle this?",
        criteria={
            "billing": "Payments, invoices, refunds, and subscription charges",
            "technical": "Software bugs and integration problems",
            "sales": "Pricing and new purchases",
        },
    )

    assert result["type"] == "choice"
    assert result["choice"] == "billing"

    assert abs(
        sum(result["probabilities"].values()) - 1.0
    ) < 1e-5
    assert 0.0 <= result["confidence"] <= 1.0


def test_choice_fast(engine):
    result = engine.choice_fast(
        state="My credit card was charged twice for the same subscription.",
        instructions="Which department should handle this?",
        criteria={
            "billing": "Payments, invoices, refunds, and subscription charges",
            "technical": "Software bugs and integration problems",
            "sales": "Pricing and new purchases",
        },
    )

    assert result["choice"] == "billing"
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-5


def test_noul_positive(engine):
    result = engine.noul(
        state=(
            "My internet is down and I need it fixed "
            "before my presentation at 3 PM."
        ),
        instructions="This person has a time-sensitive problem.",
    )

    assert result["type"] == "noul"
    assert result["noul"] > 0.5


def test_noul_negative(engine):
    result = engine.noul(
        state="I'm curious what internet plans you offer.",
        instructions="This person has a time-sensitive problem.",
    )

    assert result["noul"] < 0.5


def test_noul_with_criteria(engine):
    result = engine.noul(
        state=(
            "The user logged in from California and then "
            "from Germany ten minutes later."
        ),
        instructions="Is this login activity suspicious?",
        criteria={
            "true": (
                "The activity contains behavior inconsistent "
                "with normal legitimate account usage."
            ),
            "false": (
                "The activity is reasonably consistent "
                "with normal legitimate account usage."
            ),
        },
    )

    assert result["noul"] > 0.5


def test_score_high(engine):
    result = engine.score(
        state=(
            "I've contacted you five times already. "
            "This is ridiculous and I want this fixed NOW."
        ),
        instructions="How frustrated does the customer appear?",
        criteria=[
            "Calm and merely providing information",
            "Somewhat frustrated but still civil",
            "Extremely frustrated or angry",
        ],
    )

    assert result["type"] == "score"
    assert result["score"] > 1.0

    assert abs(
        sum(result["probabilities"].values()) - 1.0
    ) < 1e-5
    assert 0.0 <= result["confidence"] <= 1.0


def test_structured_state(engine):
    result = engine.choice(
        state={
            "customer": {
                "plan": "enterprise",
                "employees": 500,
            },
            "message": (
                "Can someone send us pricing "
                "for adding another 200 seats?"
            ),
        },
        instructions="Which department should handle this request?",
        criteria={
            "billing": "Existing invoices and payment problems",
            "technical": "Software bugs and integrations",
            "sales": "Purchasing, pricing, and account expansion",
        },
    )

    assert result["choice"] == "sales"


def test_arbitrary_labels(engine):
    result = engine.choice(
        state=(
            "The transaction is permitted by law, "
            "but could cause a substantial financial loss."
        ),
        instructions="Which category best describes the transaction?",
        criteria={
            "florp": "Legal but financially dangerous",
            "snarp": "Illegal but financially harmless",
            "glim": "Neither of the above",
        },
    )

    assert result["choice"] == "florp"
