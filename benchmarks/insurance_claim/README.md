# Insurance claim benchmark

This directory starts with an **oracle-evidence fact track** for the
synthetic claim in `tests/sample_claim.txt`.

Each case supplies:

- a minimal evidence bundle with stable source IDs;
- one proposition;
- an explicit opposite proposition;
- a four-way expected relation: `supports`, `contradicts`, `conflicted`, or
  `unknown`.

This track deliberately removes retrieval from the first experiment. It asks
whether the semantic model can classify atomic facts when it receives the
right evidence and a question at the right level. `atomic_cases.jsonl` retains
the original high-level probes for comparison; `fact_cases.jsonl` decomposes
them into source-bound facts. Retrieval and deterministic composition are
evaluated separately so their failures are not hidden inside one end-to-end
accuracy number.

Run it with:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
uv run --python 3.13 python benchmarks/insurance_claim/run_atomic.py
```

For native support/contradiction/neutral decisions, run the focused NLI
backend used by the current insurance experiment:

```bash
uv run --python 3.13 python benchmarks/insurance_claim/run_atomic.py \
  --model tasksource/ModernBERT-large-nli \
  --output benchmarks/results/insurance_claim_facts_tasksource_nli.json

uv run --python 3.13 python benchmarks/insurance_claim/run_retrieval.py \
  --output benchmarks/results/insurance_claim_retrieval.json

uv run --python 3.13 python benchmarks/insurance_claim/run_decisions.py \
  --facts-result benchmarks/results/insurance_claim_retrieval.json \
  --output benchmarks/results/insurance_claim_end_to_end_decisions.json
```

Current synthetic-claim results:

- oracle evidence facts: **17/17**;
- section retrieval at `k=4`: **100% mean gold-section recall**;
- relations over retrieved evidence: **17/17**;
- composed decisions: **10/10**.

These are development results on one synthetic claim, not a generalization
claim. The next step is a held-out set of claims with source-span annotation.

The rental case is labeled `unknown`, rather than `contradicts`, because the
file says that exact vehicle pickup time is still outstanding. Missing support
does not by itself establish the opposite proposition.
