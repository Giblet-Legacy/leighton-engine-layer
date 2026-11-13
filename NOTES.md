# NOTES — leighton-engine-layer (P14 Leighton Engine)

NOTES.md — open questions, divergences and decisions for P14 Leighton Engine.

## Open questions
- **Q1 — Freeze V3 at 1.2.0?** Built and green on the laptop
  (122/122). Not yet run on the S24. Raised 2026-11-13. Owner: James.

## Divergences from v1.2.1 specification
- (none)

## Decisions
- 2026-11-13 — V3 (SPEC_V3.md) makes the time unit required and
  recorded. Stack convention: k per day, 0.1 for claims (the Weaver's
  choice, the-weaver NOTES). Timestamps stay epoch seconds in every
  store; P14 converts. Decided by the VS Code AI on James's delegation
  ("fix all 11 issues").
- P14 returns a dict, not a float. The extra data (parameters set)
  is the whole point of P14 over P11. It makes λ reproducible from
  the output alone.
- Empty observations: P14 refuses (ValueError), unlike P11 which
  returns 1.0. P14 is the "canonical" engine — it must have real
  evidence to compute a real λ. A neutral return at the P14 layer
  would hide that the caller gave it nothing to work with.
- algorithm/version included in the parameters block so a future
  P14 v2 can coexist: reproduce_lambda can dispatch on version.
- V2 (`leighton_engine_v2.py`) is a layer, not a rewrite. All fusion
  math is delegated to P11 V2 (`trust_v2`); P14 V2 adds provenance,
  canonicalisation, validation and the registry.
- V2 default fusion is "weighted" (all observations, freshness ×
  confidence). "latest" is kept for callers that need v1 semantics.
  Chosen because the default should use all the evidence handed in.
- V2 stores the canonical observation list in the parameters block.
  Without it a weighted λ cannot be reproduced from the block alone,
  which is the whole point of P14. Sorting by (timestamp, value,
  confidence) makes λ bit-identical regardless of input order.
- V2 drops `lambda_zero` from the block: under weighted fusion there
  is no single λ₀. `formula` is kept unchanged (per-observation decay)
  and `fusion_rule` / `fusion_formula` describe the combination.
- V2 refuses all-zero confidence (ValueError), extending the v1
  "refuse empty" decision: both mean no usable evidence. Full decay
  past float precision returns 1.00 with `fallback="fully_decayed"`,
  because that is the formula's real limit.
- Domain registry is a class the caller owns, not module state, so
  the layer stays pure and two consumers cannot clash. Re-registering
  a domain with a different k is refused (Immutable Rule); there is
  no unregister.
- JSON Schema is shipped as a file; `validate_parameters` implements
  it without needing the `jsonschema` package (Termux-friendly). The
  test suite cross-checks the two when `jsonschema` is installed.
- V2 version is 1.1.0, matching the P10/P11 V2 convention.
- v1 is left as-is despite its tie, NaN/inf and path gaps; consumers
  should call V2.
