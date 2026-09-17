from opendecision.engine import OpenDecisionEngine


engine = OpenDecisionEngine()


result = engine.choice(
    state="My internet stopped working after a power outage.",
    instructions="Who should this person contact first?",
    criteria={
        "isp": "Internet provider responsible for internet service",
        "power_utility": "Company responsible for electrical service",
        "router_manufacturer": "Company that manufactured the networking hardware",
    },
)

print("\nCHOICE")
print(result)