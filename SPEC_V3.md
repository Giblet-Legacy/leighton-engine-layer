# SPEC V3 — leighton-engine-layer (P14 Leighton Engine, time-unit layer)

SPEC_V3.md — specification for leighton_engine_v3.py, the layer above P14 V2 (1.1.0).

Function:
    Closes the gap the Weaver recorded (the-weaver NOTES, "Gaps exposed
    in frozen primitives"): P14 never said what unit `k` and `t` are
    in. Three consumers made two different choices: the Weaver and the
    Echo used days, the Cockpit used seconds, so `forge trust` always
    returned 1.00. V3 makes the unit a required, recorded parameter.
    SPEC_V2.md remains authoritative for everything this document does
    not change.

Layer:     P14 — Leighton Engine, V3
Depends:   leighton_engine_v2.py (P14 V2 1.1.0)
Consumed:  The Cockpit, The Weaver, The Echo, P15 HAL
Version:   SPEC V3 1.2.0
Licence:   MSL-1.0
Author:    James Gilbert (Giblets Forge)

---

## 1. The Unit Rule

- Every Forge Stack store records time as Unix epoch **seconds**
  (P9 `created_at`, P4/P8 records, HAL seal timestamps). V3 callers
  pass observation timestamps and `reference_time` in seconds.
- `k` has unit `1 / time_unit`. `time_unit` is one of `seconds`,
  `minutes`, `hours`, `days`, and is **required**: there is no default,
  as P10 already refuses a default k ("tooling refuses to run without
  an explicit value").
- V3 converts the timestamps and `reference_time` from seconds to
  `time_unit` (dividing by 1, 60, 3600 or 86400), then calls V2.
  `computed_at` is wall-clock provenance and is not converted.
- **Stack convention:** `STACK_TIME_UNIT = "days"` and
  `STACK_CLAIM_K = 0.1` (per day) for claim decay. These are the values
  the Weaver and the Echo already used (λ₀ = 1.5 gives λ ≈ 1.18 after
  10 days). Consumers that need another calibration register a domain.

## 2. Function Contracts

### 2.1 compute_lambda(observations, k, reference_time, computed_at, *, time_unit, fusion="weighted", domain=None) -> dict

- The V2 result, computed on the converted inputs, plus two keys:
  `time_unit` (the unit of `k` and of the block's timestamps) and
  `source_time_unit` (always `"seconds"`).
- The V2 `parameters` block is unchanged in shape, so V2
  `reproduce_lambda` and `validate_parameters` accept it. Its
  timestamps are in `time_unit`.
- Failure: `time_unit` missing → TypeError (Python's own); unknown
  unit → ValueError; a bool or non-number timestamp or
  `reference_time` → TypeError before conversion. Everything else is
  V2's validation, unchanged.
- Inputs are never mutated.

### 2.2 compute_lambda_for_domain(registry, domain, observations, reference_time, computed_at, *, time_unit) -> dict

V2's domain call with V3's unit rule.

### 2.3 Re-exported unchanged from V2

`reproduce_lambda`, `validate_parameters`, `load_parameters_schema`,
`DomainRegistry`.

## 3. Tests (test_leighton_engine_v3.py)

- Public API names exist.
- `time_unit` is required; an unknown unit is a ValueError.
- With `time_unit="seconds"` V3 equals V2 called directly.
- With `days`, V3 equals V2 called on timestamps divided by 86400.
- The Weaver's anchor: λ₀ = 1.5, k = 0.1, 10 days → λ ≈ 1.18; and the
  Cockpit's old call (seconds since 1970 with k = 0.1 per second) is
  the 1.00 V3 no longer allows by accident.
- The result records `time_unit` and `source_time_unit`; V2
  `reproduce_lambda` reproduces λ from the block alone.
- Bool or string timestamp / reference_time → TypeError.
- Inputs are not mutated.
- `STACK_TIME_UNIT == "days"`, `STACK_CLAIM_K == 0.1`.

---

## Document control

- **SPEC V3 1.2.0** — 2026-11-13, by the VS Code AI on James's
  delegation ("fix all 11 issues"). Follows the Weaver's proposal and
  makes its days⁻¹ choice the recorded stack convention.
