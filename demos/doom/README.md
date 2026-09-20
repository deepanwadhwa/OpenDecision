# OpenDecision controls a bot in ViZDoom in real time

**A ~400M zero-shot model making wall-clock game decisions from structured state. No generative LLM and no visual input.**

This opt-in demo runs OpenDecision against ViZDoom's `deadly_corridor` scenario at skill 3 by default. It uses ViZDoom's `ASYNC_PLAYER` mode: Doom advances continuously at 35 tics/s while one OpenDecision worker scores the latest structured state. The previous action remains active until the next decision is ready.

## Fixed-seed real-time runs

These recordings use seed 0 and `--choice-mode fast`; they are fixed-seed traces, not a benchmark or a claimed win rate.

| Doom skill | Outcome | Health at end | Decision rate | Recording |
| --- | --- | ---: | ---: | --- |
| 1 | Goal reached; 6 kills | 100 | 5.38/s | [watch](./opendecision-doom-skill1.mp4) |
| 3 | Goal reached; 6 kills | 100 | 5.47/s | [watch](./opendecision-doom-skill3.mp4) |
| 5 | Goal reached; 6 kills | 10 | 5.4/s | [watch](./opendecision-doom-skill5-hero.mp4) |

## Setup

```bash
uv sync --python 3.13 --all-groups
uv pip install -r demos/doom/requirements.txt
```

## Run

```bash
uv run --no-sync python demos/doom/doom_demo.py \
  --record demos/doom/opendecision-doom.mp4
```

Use `--doom-skill 1` through `--doom-skill 5`; `--scenario center` and `--scenario line` remain available for the stationary defense scenarios. The overlay reports live state, policy mode, probabilities, measured choice latency, and actual decision rate. Skill, seed, and the disclosed routing details remain documented here rather than occupying the hero panel. `--execution-mode synchronous` is only a paused diagnostic mode.

Each corridor update applies a disclosed tactical router: recent damage selects `evade`; health of 40 or lower while taking damage selects `critical_evade`; enemies within 300 units select `engage`; targets at 300–450 units select `approach`; otherwise it selects `advance`. OpenDecision chooses between two tactics within that mode. A target-tracking actuator and one-tic damage reflex are also labeled in the overlay.

The model receives only compact structured state—health, ammo, kills, current-target type, enemy angle/distance, goal angle/distance, and damage—not pixels.
