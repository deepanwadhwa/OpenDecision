import pytest
from fastapi.testclient import TestClient

from opendecision.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "OpenDecision",
    }


def test_choice_api(client):
    response = client.post(
        "/v1/systemone",
        json={
            "state": (
                "My credit card was charged twice "
                "for the same subscription."
            ),
            "questions": {
                "department": {
                    "type": "choice",
                    "instructions": (
                        "Which department should handle this?"
                    ),
                    "criteria": {
                        "billing": (
                            "Payments, invoices, refunds, "
                            "and subscription charges"
                        ),
                        "technical": (
                            "Software bugs and integration problems"
                        ),
                        "sales": (
                            "Pricing and new purchases"
                        ),
                    },
                }
            },
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["answers"]["department"]["type"] == "choice"

    assert (
        body["answers"]["department"]["choice"]
        == "billing"
    )



def test_multiple_question_types(client):

    response = client.post(
        "/v1/systemone",
        json={
            "state": (
                "I was charged twice and I need this "
                "fixed before my meeting this afternoon."
            ),
            "questions": {

                "department": {
                    "type": "choice",
                    "instructions": (
                        "Which department should handle this?"
                    ),
                    "criteria": {
                        "billing": "Payments and refunds",
                        "technical": "Software problems",
                        "sales": "Purchasing questions",
                    },
                },

                "urgent": {
                    "type": "noul",
                    "instructions": (
                        "This request is time-sensitive."
                    ),
                },

                "frustration": {
                    "type": "score",
                    "instructions": (
                        "How frustrated is the customer?"
                    ),
                    "criteria": [
                        "Calm",
                        "Frustrated",
                        "Extremely angry",
                    ],
                },
            },
        },
    )

    assert response.status_code == 200

    answers = response.json()["answers"]

    assert answers["department"]["type"] == "choice"
    assert answers["urgent"]["type"] == "noul"
    assert answers["frustration"]["type"] == "score"
    assert "confidence" in answers["department"]
    assert "confidence" in answers["frustration"]
    assert "confidence" not in answers["urgent"]


def test_relation_api(client):
    response = client.post(
        "/v1/systemone",
        json={
            "state": (
                "Cervical spine X-ray: "
                "No acute fracture or dislocation."
            ),
            "questions": {
                "fracture_evidence": {
                    "type": "relation",
                    "proposition": (
                        "The X-ray found no acute fracture "
                        "or dislocation."
                    ),
                    "contradiction": (
                        "The X-ray found an acute fracture "
                        "or dislocation."
                    ),
                }
            },
        },
    )

    assert response.status_code == 200
    answer = response.json()["answers"]["fracture_evidence"]
    assert answer["type"] == "relation"
    assert answer["relation"] == "supports"


def test_document_decision_api_accepts_raw_noul_question(client):
    response = client.post(
        "/v1/documents/decide",
        json={
            "document": {
                "policy": {"collision": True},
                "claim": {"loss": "rear-end collision"},
            },
            "questions": {
                "covered": {
                    "type": "noul",
                    "instructions": "Is collision coverage active?",
                }
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    answer = body["answers"]["covered"]
    assert body["chunks"] == 1
    assert answer["type"] == "document_noul"
    assert answer["mode"] == "both"
    assert answer["status"] in {"confirmed", "tentative", "conflicted"}
    assert set(answer["binary"]["probabilities"]) == {"true", "false"}
    assert {"supports", "contradicts"}.issubset(
        answer["three_way"]["scores"]
    )
    assert answer["compiler"] == "generic_yes_no"
    assert answer["compiled"] == {
        "proposition": (
            'The answer to the question "Is collision coverage active?" '
            "is yes."
        ),
        "contradiction": (
            'The answer to the question "Is collision coverage active?" '
            "is no."
        ),
    }
    assert answer["evidence"][0]["id"] == "document"


def test_document_decision_api_can_select_binary_mode(client):
    response = client.post(
        "/v1/documents/decide",
        json={
            "document": "Collision coverage is active.",
            "noul_mode": "binary",
            "questions": {
                "covered": {
                    "type": "noul",
                    "instructions": "Is collision coverage active?",
                }
            },
        },
    )

    assert response.status_code == 200
    answer = response.json()["answers"]["covered"]
    assert answer["mode"] == "binary"
    assert answer["binary"] is not None
    assert answer["three_way"] is None
