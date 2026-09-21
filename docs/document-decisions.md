# Document decisions

`POST /v1/documents/decide` answers typed questions about plain text or JSON documents.

For each question, OpenDecision:

1. Serializes the document.
2. Keeps a small document intact.
3. Splits a long document by headings, paragraphs, and token limits.
4. Ranks sections for the question.
5. Runs the selected primitive on the relevant text.
6. Returns the answer and the source passages used.

The splitter and retriever contain no insurance or GDPR vocabulary.

## Request

```json
{
  "document": {
    "policy": {
      "collision": true,
      "deductible": 500
    },
    "claim": {
      "description": "The parked vehicle was rear-ended."
    }
  },
  "noul_mode": "both",
  "top_k": 4,
  "chunk_tokens": 384,
  "questions": {
    "covered": {
      "type": "noul",
      "instructions": "Is collision coverage active?"
    }
  }
}
```

| Field | Meaning | Default |
| --- | --- | --- |
| `document` | Plain text, JSON, or another JSON value | Required |
| `questions` | Named typed questions | Required |
| `noul_mode` | Evaluation mode for document `Noul` questions | `both` |
| `top_k` | Maximum relevant passages per answer | `4` |
| `chunk_tokens` | Maximum tokens in a document section | `384` |

## Noul modes

The mode applies only to `Noul` questions sent to the document endpoint.

### `binary`

Returns a forced `true` or `false` answer with two probabilities.

```json
{
  "mode": "binary",
  "answer": true,
  "status": "binary",
  "binary": {
    "answer": true,
    "probabilities": {"true": 0.82, "false": 0.18},
    "confidence": 0.82
  },
  "three_way": null
}
```

### `three_way`

Returns an evidence relation:

- `supports` maps to `answer: true`.
- `contradicts` maps to `answer: false`.
- `unknown` maps to `answer: null`.
- A binary NLI backend can also return `conflicted`, which maps to `answer: null`.

### `both`

Runs the binary and three-way evaluations and keeps both distributions.

| Status | Meaning | Combined answer |
| --- | --- | --- |
| `confirmed` | Binary and three-way agree. | `true` or `false` |
| `tentative` | Binary chooses an answer and three-way returns no answer. | Binary answer |
| `conflicted` | Binary and three-way disagree. | `null` |

Binary and three-way scores measure different distributions. OpenDecision keeps them separate.

Example response:

```json
{
  "type": "document_noul",
  "mode": "both",
  "answer": true,
  "status": "confirmed",
  "binary": {
    "answer": true,
    "probabilities": {"true": 0.82, "false": 0.18},
    "confidence": 0.82
  },
  "three_way": {
    "answer": true,
    "relation": "supports",
    "scores": {
      "supports": 0.76,
      "contradicts": 0.08,
      "unknown": 0.16
    }
  }
}
```

The numbers above only show the response shape.

## How raw yes/no questions are compiled

A document `Noul` question without explicit criteria uses one visible template:

```text
The answer to the question "<original question>" is yes.
The answer to the question "<original question>" is no.
```

The response includes both compiled statements in `compiled` and the compiler name in `compiler`.

Supply explicit criteria when exact wording matters:

```json
{
  "type": "noul",
  "instructions": "Is the certificate current?",
  "criteria": {
    "true": "The supplier certificate is current.",
    "false": "The supplier certificate is expired."
  }
}
```

## Evidence in responses

Every document answer includes its selected passages:

```json
{
  "evidence": [
    {
      "id": "section-004",
      "text": "Collision coverage is active with a $500 deductible.",
      "relevance": 0.93
    }
  ]
}
```

Relevance scores rank passages for the current question. Treat them as uncalibrated.

## Examples

- [Insurance claim pipeline](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/insurance_claim/README.md)
- [Structured claim through the document API](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/structured_claim/README.md)
- [Structured claim comparison](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/structured_claim/COMPARISON.md)
- [GDPR questions](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/gdpr_wiki/questions.py)
- [GDPR saved results](https://github.com/deepanwadhwa/OpenDecision/blob/main/benchmarks/results/gdpr_wiki_retrieved.json)
