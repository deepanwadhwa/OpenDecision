from opendecision.engine import OpenDecisionEngine


engine = OpenDecisionEngine()


result = engine.noul(
    state=(
        "My internet has been down since this morning "
        "and I need it fixed before my presentation at 3 PM."
    ),
    instructions="Does this person have a time-sensitive problem?",
)

print("\nNOUL")
print(result)

result = engine.noul(
    state=(
        "The user attempted to log in from Germany "
        "ten minutes after successfully logging in from California."
    ),
    instructions="Is this login activity suspicious?",
    criteria={
        "true": (
            "The activity contains behavior inconsistent with "
            "normal legitimate account usage."
        ),
        "false": (
            "The activity is reasonably consistent with "
            "normal legitimate account usage."
        ),
    },
)

print("\nNOUL WITH CRITERIA")
print(result)

result = engine.score(
    state=(
        "I've contacted you five times already. "
        "This is completely ridiculous and I want this fixed NOW."
    ),
    instructions="How frustrated does the customer appear?",
    criteria=[
        "Calm and merely providing information",
        "Somewhat frustrated but still civil",
        "Extremely frustrated or angry",
    ],
)

print("\nSCORE")
print(result)

result = engine.choice(
    state={
        "customer": {
            "plan": "enterprise",
            "employees": 500,
        },
        "message": "Can someone send us pricing for adding another 200 seats?"
    },
    instructions="Which department should handle this request?",
    criteria={
        "billing": "Existing charges, invoices and payment problems",
        "technical": "Software bugs and integration problems",
        "sales": "Purchasing, pricing and expansion discussions",
    },
)

print("\nSTRUCTURED STATE")
print(result)