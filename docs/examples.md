# Examples

OpenDecision includes runnable examples and reproducible evaluations.

## Play Doom

The ViZDoom demo sends structured game state to OpenDecision at wall-clock speed. The input contains health, ammo, targets, goal position, and recent damage.

<video class="od-video" controls playsinline preload="metadata">
  <source src="https://cdn.jsdelivr.net/gh/deepanwadhwa/OpenDecision@main/demos/doom/opendecision-doom-skill5.mp4" type="video/mp4">
  Your browser does not support embedded video. <a href="https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill5.mp4">Open the recording</a>.
</video>

[Watch Skill 1](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill1.mp4) | [Watch Skill 3](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/opendecision-doom-skill3.mp4) | [Run the demo](https://github.com/deepanwadhwa/OpenDecision/blob/main/demos/doom/README.md)

## Insurance claim

The sample claim contains a demand letter, policy facts, a police report, medical records, bills, and employer records.

| Question | Answer |
| --- | --- |
| Are the medical expenses documented? | `established` |
| Is a serious injury documented? | `refuted` |
| Is the rental need fully supported? | `unknown` |
| Are documents still outstanding? | `established` |

The development case retrieves all 17 required facts and matches all 10 composed decisions.

[Open the insurance benchmark](https://github.com/deepanwadhwa/OpenDecision/tree/main/benchmarks/insurance_claim)

## GDPR document

The GDPR example uses a 54,171-character document split into 31 sections.

| Question | Answer |
| --- | --- |
| Must a personal data breach be reported within 72 hours? | `true` |
| Must every organization appoint a Data Protection Officer? | `false` |
| Can pre-ticked boxes count as valid consent? | `false` |
| What is the maximum fine for serious infringements? | `EUR 20 million or 4% of worldwide turnover` |

The retrieval experiment answers 9 of 10 objective questions correctly.

[Open the questions](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/gdpr_wiki/questions.py) · [Open the saved results](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/gdpr_wiki_retrieved.json)

## Benchmark data

The repository includes the original 500-case Choice benchmark, TypeSafe-public-derived cases, document evaluations, and saved result files.

[Browse all benchmarks](https://github.com/deepanwadhwa/OpenDecision/tree/main/benchmarks)
