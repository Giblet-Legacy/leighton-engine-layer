# SPEC V2 — leighton-engine-layer (P14 Leighton Engine)

SPEC_V2.md — the specification for the P14 Leighton Engine V2 hardening layer.

Function:
    This document specifies `leighton_engine_v2.py`, a layer over the
    frozen `leighton_engine.py` (SPEC 1.0.0). It adds multi-observation
    weighted fusion, a domain registry for per-domain k, a JSON Schema
    for the parameters block, and a version-dispatching reproduce. SPEC.md
    remains authoritative for v1; nothing here changes v1 behaviour.

Layer:     P14 — Leighton Engine
Depends:   leighton_engine.py (P14 v1.0.0), trust_v2.py (P11 v1.1.0),
           weight_v2.py (P10 v1.1.0)
Consumed:  P15 HAL, P12 Rules, The Cockpit
Version:   SPEC_V2 1.1.0
Licence:   MSL-1.0
Author:    James Gilbert (Giblets Forge)

## 1. The Reproducibility Rule (strengthened)

Same evidence + same parameters MUST produce the same λ — bit for bit,
and regardless of the order the observations were supplied in.

V2 achieves this by:
- canonicalising the evidence: each observation is reduced to
  `{timestamp, value, confidence}` (confidence defaulting to 1.0) and
  the list is sorted by (timestamp, value, confidence) before fusion;
- storing that canonical list in the parameters block, so the block
  alone carries everything needed to recompute λ.

## 2. Fusion Rules

Both rules are computed by P11 V2; P14 never re-implements the math.

| fusion | computed by | behaviour |
|---|---|---|
| `"weighted"` (default) | `trust_v2.explain_lambda` | λ = 1.00 + Σ wᵢ(λᵢ − 1.00) / Σ wᵢ, wᵢ = cᵢ × e^(−kΔtᵢ) (P11 SPEC_V2 §1) |
| `"latest"` | `trust_v2.calculate_lambda_latest` | v1 rule; ties at the latest timestamp with different values → ValueError |

With one observation both rules equal v1.

Neutral fallbacks from P11 V2 (weighted rule):
- `"no_confidence"` (every confidence is 0) → **ValueError**. As with
  the empty stream, a neutral answer would hide that the caller gave no
  usable evidence.
- `"fully_decayed"` (Σ wᵢ underflows) → λ = 1.00, returned, with
  `fallback = "fully_decayed"` on the result. This is the true limit of
  the formula, not missing evidence.

## 3. Function Contracts

### 3.1 compute_lambda(observations, k, reference_time, computed_at, fusion="weighted", domain=None) -> dict

Validation, in order (first failure raises; inputs never mutated):
1. `fusion` not in `("weighted", "latest")` → ValueError.
2. `domain` not None and not str → TypeError; empty string → ValueError.
3. P11 V2 validation (its SPEC_V2 §2): k, reference_time, observations
   type, each observation (index named in the message).
4. Empty observations → ValueError.
5. `computed_at` non-number/bool → TypeError; NaN/inf → ValueError.

Returns:

| key | meaning |
|---|---|
| lambda | fused λ |
| parameters | the block in §4 |
| reproducible | True |
| fallback | None or `"fully_decayed"` |

### 3.2 reproduce_lambda(parameters) -> float
- Non-dict → TypeError.
- `version == "1.0.0"` → delegates to v1 `leighton_engine.reproduce_lambda`.
- `version == "1.1.0"` → `validate_parameters`, then the stored fusion
  rule over the stored observations.
- Any other version → ValueError.
- Invariant: `reproduce_lambda(r["parameters"]) == r["lambda"]` exactly,
  including after `json.loads(json.dumps(r["parameters"]))`.

### 3.3 validate_parameters(parameters) -> None
Enforces every rule in `leighton_parameters_v2.schema.json`, plus:
- all numbers finite (Python can hold NaN/inf; JSON cannot);
- `fusion_formula` matches `fusion_rule`;
- `observation_count == len(observations)`;
- `latest_observation_timestamp == max(observation timestamps)`.
Non-dict → TypeError; any other failure → ValueError.

### 3.4 load_parameters_schema() -> dict
Returns the JSON Schema (draft 2020-12) shipped beside the module.

### 3.5 DomainRegistry
Caller-owned; no module-level instance or state.
- `register(name, k, fusion="weighted") -> dict` — name a non-empty
  str; k validated by P10 V2 (bounds [1e-9, 1e9]); fusion as §2.
  Re-registering the same name with the same config is a no-op; with a
  different config → ValueError (Immutable Rule). No unregister.
- `get(name) -> dict` — a copy of `{"k", "fusion"}`; unknown → KeyError.
- `names() -> list` (sorted), `in`, `len`.

### 3.6 compute_lambda_for_domain(registry, domain, observations, reference_time, computed_at) -> dict
`compute_lambda` with k and fusion from the registry and `domain`
recorded. Registry not a `DomainRegistry` → TypeError. The parameters
block holds k, so reproducing never needs the registry.

## 4. Parameters Block (version 1.1.0)

Formally defined by `leighton_parameters_v2.schema.json`.

| key | value |
|---|---|
| algorithm | `"leighton-engine"` |
| version | `"1.1.0"` |
| formula | `"λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)"` (per-observation decay, unchanged from v1) |
| fusion_rule | `"weighted"` or `"latest"` |
| fusion_formula | the formula string for that rule |
| k | decay constant |
| reference_time | calculation time |
| latest_observation_timestamp | max observation timestamp |
| observation_count | number of observations |
| computed_at | caller-provided provenance timestamp |
| domain | domain name or null |
| observations | canonical list of `{timestamp, value, confidence}` |

Unlike v1 there is no `lambda_zero`: under weighted fusion there is no
single λ₀, and the latest value is in `observations`.

## 5. Known Limitations (P14 V2 1.1.0)

- The parameters block grows with the observation stream. Compaction or
  hashing of evidence is out of scope until a consumer needs it.
- One k per call (or per domain). Recency weighting reuses k (P11 V2).
- The registry is in-memory and per caller. Persisting domain
  calibrations is P9/P8's job.
- Still no observation ingestion from a ledger.
