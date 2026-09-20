# OpenDecision and TypeSafe Jev: structured-claim comparison

This is a small diagnostic comparison, not an official benchmark of TypeSafe
Jev. It uses one synthetic structured insurance claim and the same fourteen
`Noul` questions in both systems.

## Method

- **OpenDecision:** `tasksource/ModernBERT-large-nli`, document API,
  `noul_mode: "both"`, measured locally on 20 September 2026.
- **TypeSafe Jev:** results transcribed from the
  [shared TypeSafe playground run](https://console.typesafe.ai/playground#share/N4IgJg9gxgrgtgUwHYBcAqCAeKQC4AEIwAOiFADYCGAlnKQSSAA4TnVQCe9+jLbnAfWphupAIIAFALQB2GQBYAjAGZSAGnyk+7DgAtWYBACdRIACKUklfAFkAdOs0gEAMxcIoKagDcEpgEwADP4AbFKBilKKAKyOpFhM1EYIAM4BwTLhkTFxZBC+RpQA5qncjFCsbCnUEEjcKEYwCBqkyaiU5ALJtABGMEYpCIio3C4dgwC+LeAIYDCe1D3kfnj40YGBdoHTTMZCSFDCyCgCbHDUKNyKGxtb01UoswJgRj7GaasA2qQWVrYOIGmAGVKHB-qQALrTLAUGDVWofAjfEANShQADWAHoKnBdl4vL58C8fNQkEVcsSCil8EgICh8A9ZvhavgULoEPhtJxIdNkiwjF4yQIAO6kyDC56UDiI-DXHasdgILoIfknZIARxgSSe+WM3CCt0CUycFBodFW5SotCEIlWpAAwgAZGxSaLrfwATlypMOhlQkse6VC4TC-gAHLk+RABU8wJRA3aQEFg4FMoF5BTXgVTCCwfYKakoK8mF5aqYxChHkhDGB8NZURipHGOPgEL5UABufC+XTsZb4YWUanJShGKTIGv4Hotyx09lGfBQUf4Ums9n4FK7Tzx6Oc0fo0lFBl0ge9-spFDxmpWIwcOz4AByJ5ZbI5hyMsAuAOmoIgMH9pq0LM3DKP46x3E4bBIEqFxDDKnyMLB5oEK0CDLn0uLGPgfJUFAQzHLkFQXlcMiGsaiGPMhThMDQqD4AA1NhriktQKS6IREDEasYZkRoFFDKYNFGAeZJSIMSApLuyRLmwPSFKWdSAianGXKs8jgUafGkEhphtJe5CLsuAAUIRElKKQAJQcVxBDKGRUJOJAsDDJeCncMifI0AuqReHA8YckZEhmAAYlZSmkGGZl+SUnL6CgnGQsapCUGAABWcKPEYAi0o88GMJQMBstGpgFfFUgNNQxQrNMOUrChID2pUrHXouuqFDFaIEgg95iEwTBGLqYD3hIUr4C4MDkAZv7-vSAAkyhqGBgSshAnIKpw+jkIYRgaNEUTLX01TQSk1LNikAITA5pCAXAAi9he0ZcBa11WnAKSnEOJyKP4cAQPqOyvNGzzINQwGrEaEwTEpzADbiKApBg2CrEQ11tWDDCkCgHC7KYtITd6EkNPMCkyqQACS1KvseJ2tQUTL-tta4clyHAAOTUhUk3NSyFQFFVAD8pBJc4mCwvCikYyi2N1U4ePkATF6NAsCKmGYECpHWa38C2MLkHCLWUH15AtvFa6sdTKSCyAwu1AI76fqpktYzjiZywrRPKxJqvCEzrVc+L+C6IbuxIKe1D9lTPZ9hyg7Uj0CCHkSWbIMyodU4UeENuiK7wwg5AuFbws1sTizLGUmPS7jf7y+FICkorJcq4mADq1e1lTs3rMtxcLEsHLx61RjSSgxt1kboO1vHLjRhylgtjRHB-ighfTE570pDAbjsKDIzPVLLv1W7tf1x7JOmBTvvxpeUDsrWTnwMcV4shvW+HMcK11mlMBgOw-m+zddYUhSFYivJwoo2SklOLQC45d94y1IEfaYJ8lZn0TBfKm006I3SZOA3sad1y7DHD6I4WC2pVQZNA5eQtpi4MgaKasEBhSwOdvAkAiCnDIMbl7RMZgfZU3IJxak0BYALlofg5m602bUk6m8WmxhyGEJqGAUBqFVRPF8nnJ6TtK6u2ru7FB15SYgGbkOX2AiaZRhjLWMRvsWbsyYpqbU1ixSMJUSAPSHQBB52oEUUuMtGAsKrvjY+hMDFN3qug9cHjyBSCXAuIi9JvG+L7mNKSCc4B9AGPhOiDMsIQOpCzNxLhCjfwEC4Kg5I96BN0cEpBoSuFGLEMkJmzSxS-3igMNc8YByjkKHRawxSCq1mSN4UGwo3G6HgJYZUoyEBMKqTow+eiQkN09kYkxBSpQuTHv1QaU4ZyFQgH5R47dXjkNwUvTWky-KhxSulC8xh7EjLGW4m5MBPHPLmcwxZstll1NWag+qQJ9ATXbvdRcr0pwcgGoVJk08FxvI6JiDehDRmSQXJ84UUL4XMylEvNxUEYKUXXvAb5B9fm1I4fUtZqtVpU2wbWQlwDKKtQvNIsAtYYBMA-lTeK+k6y-RmhCs0sw3EbzkhAIoT8JY8AruShBfyqUAsMefSm85Z5rSrF4Doo94xSDGBNekECjC1iEljX29d+hYQqKCzk-QN4cnhRuGAEqpUKSYrzYwHBC5Qw0CAQ21AABq7xrzI28IoaGgxlieFmDYCAhhyApC+CAVKbYpBUFyjgCEEwgA), as supplied by the
  project maintainer. The Jev model/version is not asserted here.
- Percentages are model outputs, not calibrated probabilities of correctness.
- `S`, `C`, and `U` below mean supports, contradicts, and unknown.

## Evidence-grounded core

These ten questions can be evaluated against facts, policy fields, arithmetic,
dates, or explicit document requirements. This is the primary scored subset.

| Question | Expected | OpenDecision binary | OpenDecision three-way | TypeSafe Jev |
| --- | ---: | --- | --- | --- |
| `covered` | True | **T 98.5%** / F 1.5% | **S 98.4%** / C 0.3% / U 1.3% | **T 51%** / F 49% |
| `exclusion` | False | **T 86.6%** / F 13.4% | **S 68.5%** / C 22.5% / U 9.0% | **T 53%** / F 47% |
| `on_circuit` | False | T 1.9% / **F 98.1%** | S 1.5% / **C 98.1%** / U 0.4% | T 3% / **F 97%** |
| `deductible` | True | **T 84.1%** / F 15.9% | **S 70.0%** / C 16.9% / U 13.1% | **T 75%** / F 25% |
| `docs_sufficient` | False | T 40.4% / **F 59.6%** | S 27.7% / C 18.3% / **U 54.0%** | T 32% / **F 68%** |
| `within_limit` | True | **T 69.3%** / F 30.7% | **S 83.5%** / C 13.5% / U 3.0% | **T 98%** / F 2% |
| `within_window` | True | **T 87.5%** / F 12.5% | **S 87.3%** / C 9.1% / U 3.6% | **T 97%** / F 3% |
| `reported_timely` | True | **T 53.7%** / F 46.3% | **S 61.1%** / C 29.7% / U 9.2% | **T 93%** / F 7% |
| `rental_eligible` | False | T 2.6% / **F 97.4%** | S 1.9% / **C 97.8%** / U 0.3% | T 4% / **F 96%** |
| `line_items_sum` | True | **T 92.5%** / F 7.5% | **S 92.4%** / C 5.5% / U 2.1% | **T 90%** / F 10% |

On this core subset:

- OpenDecision binary/both matches **9/10** expected labels.
- TypeSafe Jev matches **9/10** expected labels.
- Both systems miss `exclusion`, apparently over-weighting the phrase
  “track-day event” despite the vehicle being stationary in spectator parking
  and explicitly not on the circuit.
- OpenDecision three-way returns eight correct relations, one incorrect
  relation (`exclusion`), and one abstention (`docs_sufficient`).

## Exploratory inference and policy questions

These questions are reported separately and are not included in the primary
accuracy figure. They require an unstated policy threshold, inference from an
absence, or a recommendation rather than a directly specified rule.

| Question | Provisional interpretation | OpenDecision binary | OpenDecision three-way | TypeSafe Jev |
| --- | --- | --- | --- | --- |
| `fraud_flag` | False, but no fraud-review policy is supplied | **T 53.4%** / F 46.6% | S 11.5% / C 29.6% / **U 58.9%** | T 43% / **F 57%** |
| `human_review` | True if `auto-triage` implies no human review | T 33.4% / **F 66.6%** | S 12.4% / C 17.7% / **U 70.0%** | **T 85%** / F 15% |
| `manual_review` | True under the benchmark author's review policy | T 29.6% / **F 70.4%** | S 5.8% / C 44.5% / **U 49.7%** | **T 82%** / F 18% |
| `subrogation` | True if the rear-ending car is treated as potentially liable | T 43.1% / **F 56.9%** | S 4.8% / C 35.5% / **U 59.7%** | **T 83%** / F 17% |

Jev's high `human_review` and `manual_review` scores are notable, but this
single run cannot establish why the model is confident. OpenDecision's
three-way abstentions accurately expose that these propositions are not
directly established by one explicit document statement. Its forced binary
answers nevertheless disagree with the provisional interpretations.

## Benchmark-design consequence

Future versions should preserve the original exploratory questions but add
more atomic, auditable counterparts:

- `fraud_flag`: first test explicit indicators; apply a supplied fraud-review
  threshold separately.
- `human_review`: ask whether `auto-triage` authored the approval and whether a
  human reviewer is recorded as two separate facts.
- `manual_review`: supply an explicit routing rule and evaluate it
  deterministically from established facts.
- `subrogation`: first establish that another vehicle rear-ended the insured
  vehicle; apply a separate subrogation-eligibility rule.

This separation tests semantic evidence extraction independently from policy
logic and avoids rewarding a model merely for making a plausible guess.
