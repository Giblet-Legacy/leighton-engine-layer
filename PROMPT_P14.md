# P14 Leighton Engine — Laptop Audit Prompt

P14 leighton-engine-layer is frozen at v1.0.0 on the phone with 11/11 tests passing.

## Your Task

1. Pull `Giblet-Legacy/leighton-engine-layer`.
2. Audit against SPEC.md and CHANGELOG.md.
3. Run `pytest -q` — expect 11 passed.
4. If you find gaps, create `leighton_engine_v2.py` (do NOT edit v1).
5. Suggested V2 hardening: support multiple observation weighting in the `compute_lambda` method (currently passes only the latest to P11), handle multiple domains via a registry, and add a JSON Schema for the `parameters` block to formally validate reproducibility.
6. Push when green so the phone can verify.
