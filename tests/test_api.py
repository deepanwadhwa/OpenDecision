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