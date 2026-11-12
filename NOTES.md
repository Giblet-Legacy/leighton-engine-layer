# NOTES — leighton-engine-layer (P14 Leighton Engine)

NOTES.md — open questions, divergences and decisions for P14 Leighton Engine.

## Open questions
- (none)

## Divergences from v1.2.1 specification
- (none)

## Decisions
- P14 returns a dict, not a float. The extra data (parameters set)
  is the whole point of P14 over P11. It makes λ reproducible from
  the output alone.
- Empty observations: P14 refuses (ValueError), unlike P11 which
  returns 1.0. P14 is the "canonical" engine — it must have real
  evidence to compute a real λ. A neutral return at the P14 layer
  would hide that the caller gave it nothing to work with.
- algorithm/version included in the parameters block so a future
  P14 v2 can coexist: reproduce_lambda can dispatch on version.
