from transformers import pipeline

classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/ModernBERT-large-zeroshot-v2.0"
)

result = classifier(
    "Statement: My internet stopped working after a power outage..\
        Who should this person contact first?",
    candidate_labels=["ISP = Internet provider responsible for internet service", 
                      "Power utility = Company responsible for electrical service", 
                      "Router manufacturer = Company that manufactured the networking hardware"],
    multi_label=False,
)

print(result)