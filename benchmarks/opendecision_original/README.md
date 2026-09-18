# OpenDecision Original Choice 500

A synthetic, original evaluation set for OpenDecision Choice classification.

## Contents

- `cases.jsonl` — all 500 original Choice cases
- `dev.jsonl` — 375-case development split
- `holdout.jsonl` — 125-case untouched evaluation split
- `manifest.json` — domain counts and exact split membership

## Scope

The dataset contains **500 original Choice cases across 25 domains**, with **20 cases per domain**.

Domains:

1. support routing
2. function/tool routing
3. citation relation
4. semantic extraction
5. date semantics
6. product taxonomy
7. entity matching
8. science phenomena
9. word sense
10. policy decisions
11. software bug classification
12. document type
13. logistics exceptions
14. transaction type
15. manufacturing defects
16. job-family routing
17. email intent
18. machine-learning task type
19. appliance troubleshooting
20. research-method classification
21. security-event classification
22. contract-clause classification
23. meeting intent
24. return reasons
25. database-operation intent

## Schema

Every row follows the OpenDecision Choice schema:

```json
{
  "id": "od_support_routing_001",
  "type": "choice",
  "domain": "support_routing",
  "state": "...",
  "instructions": "...",
  "criteria": {
    "label_a": "semantic description",
    "label_b": "semantic description"
  },
  "expected": "label_a"
}
```

The extra `domain` field can be ignored by existing evaluation code.

## Split policy

The split is deterministic and stratified within each domain:

- **375 development cases** — 15 from every domain
- **125 holdout cases** — 5 from every domain
- random seed: `20260918`

Use `dev.jsonl` for compiler ablations, routing experiments, prompt/compiler selection, and error analysis.

Do **not** use `holdout.jsonl` to select compiler profiles or routing rules. Evaluate it only after the system design is frozen.

## Provenance

These are original synthetic cases created for OpenDecision. They are not copied from TypeSafe, Jev, OpenJev, or another benchmark.

The dataset intentionally mixes:
- ordinary semantic classification,
- close semantic alternatives,
- structured state,
- domain terminology,
- tool routing,
- evidence relations,
- policy interpretation,
- taxonomy classification,
- and extraction-like Choice tasks.

## Recommended reporting

Report:
- overall Choice accuracy,
- per-domain accuracy,
- compiler profile,
- model/backend,
- and whether results are on `dev` or `holdout`.

For compiler experiments, report all tested profiles rather than only the winner.

For perturbation experiments, generate variants into a separate dataset so they are not counted as additional original cases.
