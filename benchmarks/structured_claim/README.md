# Structured claim through the document API

This case sends one structured JSON document and the fourteen user-supplied
`Noul` questions to `POST /v1/documents/decide`.

The production document pipeline contains no insurance vocabulary or rules.
Every question without explicit criteria is compiled using the same visible
template:

```text
The answer to the question "<original question>" is yes.
The answer to the question "<original question>" is no.
```

The saved request selects `noul_mode: "both"`. The API therefore exposes a
forced binary preference and an independent three-way evidence judgment for
each question. Its combined `status` is:

- `confirmed` when binary and three-way agree;
- `tentative` when binary chooses an answer and three-way returns `unknown`;
- `conflicted` when the two disagree, in which case the combined answer is
  `null`.

This OpenDecision output is suitable for comparison with the separate
two-class TypeSafe Jev results, but the scores are model-specific and should
not be treated as calibrated or directly interchangeable.

See [COMPARISON.md](COMPARISON.md) for the complete probability table, the
10-question evidence-grounded core, and the separately reported exploratory
questions.

`expected.json` is benchmark data, not application logic. Its labels encode
the following interpretation of the sample:

- the spectator-parking collision is covered and is not track/competitive
  driving;
- the $500 deductible applies;
- a police report is missing for a claim over the policy's $2,000 threshold;
- $3,250 is below the $10,000 limit;
- the incident and report dates satisfy the policy dates and ten-day window;
- rental reimbursement is absent;
- two recent claims alone are not treated as a fraud indicator;
- the `auto-triage` note is an automated approval, not human review;
- the claim should be manually reviewed because the approval overlooks the
  deductible, rental exclusion, and missing police report;
- the line items total $3,250; and
- the other car is a potentially at-fault third party.

The fraud and manual-review labels are policy judgments rather than facts
explicitly stated in the source. They should be interpreted accordingly.

With the API running:

```bash
uv run --python 3.13 python benchmarks/structured_claim/run_api.py
```

With `tasksource/ModernBERT-large-nli`, the current `both` run matches 9 of the
14 benchmark labels. Nine answers are confirmed (eight match the labels), and
five are tentative binary preferences after a three-way abstention (one
matches). The track-exclusion answer is an incorrect confirmed result,
demonstrating that agreement between two formulations of one model is not
independent proof.
