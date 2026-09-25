# Model selection and evaluation

OpenDecision uses `MoritzLaurer/ModernBERT-large-zeroshot-v2.0` by default. `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` is available as an explicit option. The same `Choice`, `Noul`, `Score`, and document APIs work with either model.

## Select DeBERTa

In Python:

```python
from opendecision import OpenDecisionEngine

engine = OpenDecisionEngine(
    model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0"
)
```

For the server, set `OPENDECISION_MODEL=MoritzLaurer/deberta-v3-large-zeroshot-v2.0` before running `opendecision serve`, or pass `opendecision serve --model MoritzLaurer/deberta-v3-large-zeroshot-v2.0`. Model selection applies to the whole server process; the `model` field in an individual `/v1/systemone` request does not switch models.

## What the project measured

On September 25, 2026, we compared both models on the same fixed cases. The standard `choice()` formulation uses two classifier calls and a third call if they disagree. The experimental single pass formulation uses the state and criterion descriptions with the pipeline's default hypothesis. It is **not** the package default. Counts below are correct Choice predictions:

| Model | Choice formulation | Original 125 case holdout | Public-derived 51 Choice cases |
| --- | --- | ---: | ---: |
| ModernBERT | Standard | 108/125 | 43/51 |
| DeBERTa | Standard | 112/125 | 35/51 |
| ModernBERT | Experimental single pass | 97/125 | 27/51 |
| DeBERTa | Experimental single pass | 107/125 | 31/51 |

The 125 case holdout is [OpenDecision's synthetic Choice set](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/opendecision_original/README.md). The 51 cases are part of a [public documentation derived set](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/typesafe_public/SOURCES.md), not an official TypeSafe benchmark. The standard ModernBERT results are saved in [`opendecision_v0.1_production_holdout.json`](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/opendecision_v0.1_production_holdout.json) and [`opendecision_v0.1_typesafe_public.json`](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/opendecision_v0.1_typesafe_public.json). The other Choice combinations were run locally against the same fixed cases for this comparison. A [summary of all measured results](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/model_selection_2026-09-25.json) is saved in the repository. The experimental single pass formulation is distinct from the public `choice_fast()` method.

On the same 80 case public-derived set, the saved default ModernBERT run answered 17/20 `Noul` cases correctly and had a `Score` mean absolute error of 0.375 across nine cases. A local DeBERTa run answered 14/20 `Noul` cases correctly and had a `Score` mean absolute error of 0.347. These are small samples, and document workflows were not compared end to end across the two models.

The models also have different context limits: [ModernBERT allows 8,192 tokens](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0/blob/main/config.json) and [DeBERTa allows 512](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0/blob/main/config.json). OpenDecision truncates direct NLI inputs to the selected model's limit. This matters when state or evidence is long.

These results do not show a consistent quality gain from switching the package default to DeBERTa. Choose a model using representative cases from your application, and treat returned scores as uncalibrated.
