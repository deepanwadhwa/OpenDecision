# TypeSafe-public evaluation set

This file documents the provenance of `cases.jsonl`.

## Scope

- **80 cases total**
- **51 Choice**
- **20 Noul**
- **9 Score**

The JSONL uses the same schema as OpenDecision's existing `benchmarks/cases.jsonl`.

These cases are **adapted from public TypeSafe documentation and cookbooks**. They are not a verbatim copy of TypeSafe's benchmark files. Wording is shortened or paraphrased where practical so each case is self-contained and suitable as an OpenDecision evaluation fixture.

The `expected` field is a semantic target for OpenDecision. It is **not** a copy of Jev's probability or confidence. Borderline examples without a defensible target were generally excluded.

## Source groups

### `ts_date_*`

Source: TypeSafe **Date extraction** cookbook  
https://docs.typesafe.ai/cookbooks/date_extraction_cookbook

The cookbook decomposes date extraction into closed-set questions for absolute vs relative dates, month, day, year, relative-day anchor, weekday, and week qualifier.

Provenance: **paraphrased / structurally adapted**

### `ts_func_*`

Source: TypeSafe **Function calling** cookbook  
https://docs.typesafe.ai/cookbooks/function_calling

The cookbook publishes fourteen natural-language trading commands and the function selected for each. The eval preserves those task mappings while paraphrasing the commands.

Provenance: **paraphrased**

### `ts_extract_*`

Source: TypeSafe **Pre-parsed value extraction** cookbook  
https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook

Covers the public email, phone, country, currency, total-due, courtesy-credit, and credit-vs-charge examples.

Provenance: **paraphrased / structurally adapted**

### `ts_insurance_*`

Source: TypeSafe **Self-consistency: nouls** cookbook  
https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook

Uses a condensed version of the public auto-insurance claim. Only clear factual questions were retained. Borderline questions such as overall exclusion/coverage judgment were intentionally omitted.

Provenance: **paraphrased / condensed**

### `ts_score_bug_*`

Source: TypeSafe **Score** documentation  
https://docs.typesafe.ai/primitives/score

Uses the public bug-severity scale and five example situations. Fractional Jev outputs are not used as ground truth; the semantic dominant level is used instead.

Provenance: **paraphrased**

### `ts_entity_score_*`, `ts_entity_noul_*`

Source: TypeSafe **Knowledge graph entity alignment** cookbook  
https://docs.typesafe.ai/cookbooks/entity_alignment

Uses the four public beer-pair examples (`c446`, `c427`, `c100`, `c428`) and the cookbook's three semantic relation levels.

Provenance: **adapted from public examples**

### `ts_citation_*`

Source: TypeSafe **Double-checking citations** cookbook  
https://docs.typesafe.ai/cookbooks/citation_check

The cookbook evaluates JWT claims using `supports / contradicts / says_nothing`. These cases preserve the published relation targets while condensing the RFC context into self-contained summaries.

Provenance: **derived / paraphrased**

### `ts_hier_*`

Source: TypeSafe **Hierarchical classification** cookbook  
https://docs.typesafe.ai/cookbooks/hierarchical_classification

Uses the four public target examples: bird perches, a cat window bed, Crohn disease, and `retrievers.py`. The original hierarchies are large, so these cases collapse each into a small final-label candidate set.

Provenance: **derived from public examples**

## Important distinction

This is a **TypeSafe-public-derived OpenDecision eval set**, not an official TypeSafe benchmark and not a claim of exact Jev reproduction.

For published results, a precise description is:

> Evaluated on N cases adapted from public TypeSafe documentation examples.

## Documentation index

https://docs.typesafe.ai/llms.txt
