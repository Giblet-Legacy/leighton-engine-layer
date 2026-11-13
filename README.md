# leighton-engine-layer — P14 Leighton Engine

README.md — repository purpose and layer contract for P14 Leighton Engine.

Function:
    This repository implements primitive layer P14 of the Forge Stack:
    the canonical Leighton Engine. It orchestrates P10 and P11 to
    produce a canonical λ from an observation stream, and returns
    the complete parameter set so the result is reproducible.

Layer:    P14 — Leighton Engine
Depends:  P10 Weight, P11 Trust (leighton_engine_v2.py needs
          weight_v2.py P10 v1.1.0 and trust_v2.py P11 v1.1.0)
Consumed: P15 HAL, P12 Rules, The Cockpit
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
Status:   1.1.0 (v1 frozen at 1.0.0; V2 hardening layer added).
          V3 time-unit layer (leighton_engine_v3.py, SPEC_V3.md, 1.2.0)
          frozen. New code imports leighton_engine_v3.

Files:
    leighton_engine.py                  — v1.0.0, frozen. Latest observation
                                          wins. (SPEC.md)
    leighton_engine_v2.py               — V2 layer: weighted fusion, domain
                                          registry, version-dispatching
                                          reproduce. (SPEC_V2.md)
    leighton_parameters_v2.schema.json  — JSON Schema for the V2
                                          parameters block.
    conftest.py                         — puts ../weight-layer and
                                          ../trust-layer on sys.path for pytest.

Expects weight-layer and trust-layer checked out as sibling directories
(../weight-layer, ../trust-layer). Run `pytest -q` from any directory.
