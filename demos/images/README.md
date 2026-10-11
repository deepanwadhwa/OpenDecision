# Image questions and composed decisions

This demo keeps question definitions, model scoring, and application policy
separate. It uses the same `/v1/systemone` request and response as the server.
The images stay in your own directory; none are included here.

From the repository:

```bash
uv sync --extra images --all-groups
uv run --extra images python demos/images/run.py /path/to/images
```

The default runner exercises the real FastAPI route in process with SigLIP2,
without loading the text model. It uses FastAPI's test client from the development
dependencies. To test a running server instead:

```bash
opendecision serve
uv run --extra images python demos/images/run.py /path/to/images \
  --api-url http://127.0.0.1:8000
```

Edit `questions.json` to provide image filenames, typed questions, candidate
captions, and optional expected answers. `expected: null` leaves ambiguous
questions unscored. For Noul, expectations are booleans; for Choice, they are
candidate keys. Thresholds live at the top of the manifest.

The included captions were developed by inspecting the supplied images and
baseline errors. The animal options include cat, dog, coyote, bear, another
animal, and no animal. Counting includes a zero option instead of forcing a
one-versus-many answer. Concrete true/false captions avoid some negation failures,
but these sample-specific alternatives are not universal absence detectors.
A correct winner with a weak probability is still weak evidence.

The original prompts are retained in `questions-baseline.json`. Compare them:

```bash
uv run --extra images python demos/images/run.py /path/to/images \
  --questions demos/images/questions-baseline.json \
  --output build/image-evaluation/baseline-results.json

uv run --extra images python demos/images/run.py /path/to/images \
  --compare-raw-noul --output build/image-evaluation/final-results.json
```

`--compare-raw-noul` also evaluates Noul without explicit criteria. Those raw
sigmoid match scores often differ substantially from relative two-caption scores.
Do not assume that the same threshold works for both. Results include the exact
questions, API responses, visual checks, timing, and alarm traces. Output goes
under ignored `build/` so private evaluation artifacts stay local.

## Composing the alarm

The runner applies this application policy to cases with both relevant answers:

```python
animal_present = answers["animal_present"]["noul"] >= 0.5
kind = answers["animal_type"]
is_bear = kind["choice"] == "bear"
choice_is_strong = kind["probabilities"][kind["choice"]] >= 0.6
sound_alarm = animal_present and is_bear and choice_is_strong
```

`alarm_decision` translates those comparisons into facts and calls the existing
`evaluate_rule({"all": ["animal_present", "animal_is_bear"]}, facts)`.
A missing or weak Choice becomes `unknown`; only an `established` result returns
`sound_alarm`. These are simulated action labels, without triggering a speaker
or external device. The fact trace and threshold policy accompany every decision.

The thresholds are demonstration settings, not calibrated safety guarantees.
The bear photo is a positive control and the cat surveillance scene is a negative
control. Counting, negation, precise species identification, and flood context
remain limitations of the model.

## Bin and fence decisions

`binn.jpg` asks whether a bin is present, whether it is empty, contained, or
overflowing, and whether litter is scattered on the floor. The composed rule
returns `request_collection` when the bin is present and the overflowing Choice
passes the probability threshold.

`fenn.jpg` asks whether a fence is present, its condition, and its material.
The composed rule returns `create_repair_task` when the fence is present and
the damaged Choice passes the threshold. Material is a diagnostic question and
does not control the repair decision.

Each case can define a `decision` with `presence_question`, `choice_question`,
`target_choice`, `action`, and `otherwise`. The shared policy helper composes
these answers using the existing rule evaluator. No external action is executed.

## Visual report

After running the evaluation, generate a self-contained HTML report:

```bash
uv run --extra images python demos/images/render_report.py \
  build/image-evaluation/final-results.json /path/to/images
```

The report embeds each image alongside its exact questions, candidate captions,
returned answers, expected results, and composed decision trace. It works offline
and defaults to `build/image-evaluation/report.html`. Use `--output` to change
the destination. The file contains your photos; keep it local unless you intend
to share them.

## API call times

```bash
uv run --extra images python demos/images/measure_latency.py /path/to/images
```

This measures real local HTTP requests with preloaded text and image models.
It runs one warmup per payload and records five calls. The output includes the
median, range, individual times, question counts, and responses. Homepage image
payloads contain the displayed questions. Full gallery payloads contain every
question for each image. Results are saved in `build/image-evaluation/api-timings.json`.
