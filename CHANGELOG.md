# CHANGELOG — leighton-engine-layer (P14 Leighton Engine)

CHANGELOG.md — build history for P14 Leighton Engine, latest entry at top.

## [v1.1.0] — 2026-11-12

### Good
- Laptop audit per PROMPT_P14.md: v1 confirmed 11/11 green.
- `leighton_engine_v2.py` added as a layer over v1 (v1 untouched),
  specified in `SPEC_V2.md`, tested by `test_leighton_engine_v2.py`.
  112/112 tests pass (11 v1 + 101 V2).
- All three suggested hardenings adopted:
  - Multi-observation weighted fusion (default) via P11 V2; the v1
    latest-wins rule stays available as `fusion="latest"`.
  - `DomainRegistry`: caller-owned name → (k, fusion); conflicting
    re-registration refused. `compute_lambda_for_domain` records the
    domain in the parameters block.
  - `leighton_parameters_v2.schema.json` (JSON Schema 2020-12) plus a
    dependency-free `validate_parameters` that also checks cross-field
    rules. A test confirms `jsonschema` and the validator agree.
- Parameters block now carries the canonical (sorted) evidence, so λ
  is reproducible bit for bit from the block alone, in any input
  order, and after a JSON round trip.
- `reproduce_lambda` (V2) dispatches on version: v1.0.0 blocks still
  reproduce through the frozen v1 function.
- `conftest.py` puts `../weight-layer` and `../trust-layer` on
  sys.path relative to the repo, so pytest runs from any directory.

### Bad
- Audit found v1 violates its own Reproducibility Rule: two
  observations at the latest timestamp with different values give an
  order-dependent λ (e.g. 1.368 vs 0.816). Fixed in V2 (weighted
  averages ties; latest rejects them as ambiguous), not in v1
  (Immutable Rule).
- v1 accepts non-finite input: NaN value returns NaN;
  `reference_time=inf` returns 1.00. A string `observations` gives a
  misleading "missing 'timestamp'" error. Fixed in V2.
- v1 resolves sibling paths against the CWD, so pytest failed outside
  the repo root (collection error). Fixed by `conftest.py`.
- README status still read "0.0.0-dev" after the v1.0.0 freeze, and
  the scaffold CHANGELOG entry had no header. Corrected.

### Ugly
- v1 imports `trust` (P11) but never calls it; it re-implements P11's
  latest-wins logic, contrary to SPEC §3 ("delegates to P11"). V2
  delegates for real. v1 left as-is.
- V2 needs P10 v1.1.0 and P11 v1.1.0 on the phone for its tests.
- The V2 parameters block grows with the observation stream (see
  SPEC_V2 §5).

## [v1.0.0] — 2026-11-12

### Good
- `leighton_engine.py` implemented to SPEC v1.0.0.
- 11/11 pytest tests pass.
- Canonical λ computation returning full parameter provenance.
- `reproduce_lambda` allows any independent implementation to verify the result.
- Refuses empty observation streams.

### Bad
- (none)

### Ugly
- (none)

## [0.0.0-dev] — scaffold

### Good
- Repository scaffolded: `Giblet-Legacy/leighton-engine-layer` created for P14.
- Depends on P10 Weight v1.0.0 and P11 Trust v1.0.0.

### Bad
- (none)

### Ugly
- (none)
