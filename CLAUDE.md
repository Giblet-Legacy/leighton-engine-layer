# Forge Stack Context — P14 Leighton Engine

CLAUDE.md — Context briefing for AI assistants working in this repository.

## The Immutable Rule
Never rewrite a primitive. Add a layer.

## Dual-Device Workflow
We build on an S24 (Termux) and a laptop (VS Code). State is confirmed, never assumed. Always use LF line endings. Commit messages must be clear. We use the Good/Bad/Ugly CHANGELOG format (latest at top).

## Header Discipline
Every file MUST have a top header paragraph explaining its function.
Every function MUST have a numbered header.

## P14 Architecture Specifics
- Depends on `weight` (P10) and `trust` (P11).
- Current layer: `leighton_engine_v3.py` (SPEC_V3.md, frozen 1.2.0). `time_unit` is required; timestamps are epoch seconds; stack convention is k per day (`STACK_CLAIM_K = 0.1`). New code imports `leighton_engine_v3`.
- Canonical λ computation from an observation stream.
- Returns the λ value PLUS all parameters used, so results are reproducible.
- Same evidence + same parameters MUST produce same λ.
