from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(
    api_key="local",
    base_url="http://127.0.0.1:8000",
)

response = client.system_one(
    state="I was charged twice and need this fixed before my meeting.",
    questions={
        "department": Choice(
            instructions="Which department should handle this?",
            criteria={
                "billing": "Payments and refunds",
                "technical": "Software problems",
                "sales": "Purchasing questions",
            },
        ),
        "urgent": Noul(
            instructions="This request is time-sensitive.",
        ),
        "frustration": Score(
            instructions="How frustrated is the customer?",
            criteria=[
                "Calm",
                "Frustrated",
                "Extremely angry",
            ],
        ),
    },
)

print(response)