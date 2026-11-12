# SPEC — leighton-engine-layer (P14 Leighton Engine)

SPEC.md — the complete layer specification for P14 Leighton Engine.

Function:
    This document is the authoritative specification for primitive
    layer P14 of the Forge Stack. It defines the canonical λ
    computation from an observation stream, with full parameter
    tracking so results are reproducible.

Layer:     P14 — Leighton Engine
Depends:   P10 Weight, P11 Trust
Consumed:  P15 HAL, P12 Rules, The Cockpit
Version:   SPEC 1.0.0
Licence:   MSL-1.0
Author:    James Gilbert (Giblets Forge)

## 1. The Reproducibility Rule

The same evidence and the same parameters MUST produce the same λ.
P14 enforces this by returning not just the λ value, but the
complete set of parameters used to produce it:

- algorithm: "leighton-engine"
- version: "1.0.0"
- formula: "λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)"
- lambda_zero
- k
- reference_time
- latest_observation_timestamp
- observation_count
- computed_at (caller-provided timestamp)

Given this return object alone, any independent implementation
must be able to recompute λ and arrive at the same value.

## 2. Function Contracts

### 2.1 compute_lambda(observations: list[dict], k: float, reference_time: float, computed_at: float) -> dict
- Input:
  - observations: list of dicts with "timestamp" and "value".
  - k: decay constant, must be > 0.
  - reference_time: the calculation time.
  - computed_at: caller-provided wall-clock timestamp for provenance.
- Output: dict with keys `lambda`, `parameters` (the full parameter
  set above), and `reproducible` (boolean, always True on success).
- Failure:
  - ValueError if k is missing or <= 0.
  - ValueError if reference_time < latest observation timestamp.
  - ValueError if observations is empty (P14 refuses empty streams,
    unlike P11 which returns 1.0).
  - ValueError if any observation is missing timestamp or value.

### 2.2 reproduce_lambda(parameters: dict) -> float
- Input: a parameters dict as produced by compute_lambda.
- Output: the recomputed λ value.
- Invariant: `reproduce_lambda(compute_lambda(...)["parameters"])` MUST
  equal `compute_lambda(...)["lambda"]` for any valid input.
- Failure: ValueError if the parameters dict is missing required keys
  or contains a mismatched algorithm/version.

## 3. Known Limitations (P14 v1.0.0)

- Simple fusion: delegates to P11, which uses the most recent
  observation. Sophisticated multi-observation fusion is a P11 v2
  concern.
- No persistence. P14 returns data; storage is P9/P8's job.
- No observation ingestion. P14 accepts observations as given.
  Extracting them from a ledger is out of scope for v1.
