"""
leighton_engine_v3.py — P14 Leighton Engine V3, the time-unit layer over V2

Function:
    The layer new code imports instead of leighton_engine_v2.py. It
    makes the unit of k and t a required, recorded parameter
    (SPEC_V3.md): callers pass epoch-second timestamps and name the
    unit k is in; V3 converts and delegates every calculation to V2.
    Records the stack convention: k per day, 0.1 for claim decay.

    leighton_engine.py and leighton_engine_v2.py are not edited
    (Immutable Rule).

Public API:
    1. compute_lambda            — V2, with the unit rule
    2. compute_lambda_for_domain — V2 domain call, with the unit rule
    (re-exported from V2: reproduce_lambda, validate_parameters,
     load_parameters_schema, DomainRegistry)

Internal helpers (not exported):
    3. _seconds — check one epoch-second value (TypeError for bool / non-number)
    4. _convert — observations and reference_time from seconds to the unit

Layer:    P14 — Leighton Engine, V3
Depends:  leighton_engine_v2.py (P14 V2 1.1.0)
Consumed: The Cockpit, The Weaver, The Echo, P15 HAL
Spec:     SPEC_V3.md 1.2.0
Version:  1.2.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _path in (os.path.join(_PARENT, "weight-layer"), os.path.join(_PARENT, "trust-layer"), _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import leighton_engine_v2 as _v2  # noqa: E402

reproduce_lambda = _v2.reproduce_lambda
validate_parameters = _v2.validate_parameters
load_parameters_schema = _v2.load_parameters_schema
DomainRegistry = _v2.DomainRegistry

TIME_UNITS = {"seconds": 1.0, "minutes": 60.0, "hours": 3600.0, "days": 86400.0}
STACK_TIME_UNIT = "days"
STACK_CLAIM_K = 0.1
SOURCE_TIME_UNIT = "seconds"


# ---------------------------------------------------------------------------
# 3. _seconds
#    An epoch-second value must be a real number before it is divided;
#    True / 86400 would otherwise slip past V2's bool check as a float.
# ---------------------------------------------------------------------------
def _seconds(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number of seconds, got {type(value).__name__}")
    return value


# ---------------------------------------------------------------------------
# 4. _convert
#    Returns (observations, reference_time) in time_unit. Observation
#    dicts are copied; a missing timestamp is passed through for V2 to
#    report in its own words. Unknown unit → ValueError.
# ---------------------------------------------------------------------------
def _convert(observations, reference_time, time_unit):
    if time_unit not in TIME_UNITS:
        raise ValueError(f"time_unit must be one of {sorted(TIME_UNITS)}, got {time_unit!r}")
    scale = TIME_UNITS[time_unit]
    ref = _seconds("reference_time", reference_time) / scale
    if not isinstance(observations, list):
        return observations, ref  # V2 / P11 V2 report the type error
    converted = []
    for i, obs in enumerate(observations):
        if isinstance(obs, dict) and "timestamp" in obs:
            obs = dict(obs, timestamp=_seconds(f"observations[{i}].timestamp", obs["timestamp"]) / scale)
        converted.append(obs)
    return converted, ref


# ---------------------------------------------------------------------------
# 1. compute_lambda
#    SPEC_V3 §2.1. time_unit is keyword-only and has no default.
# ---------------------------------------------------------------------------
def compute_lambda(observations, k, reference_time, computed_at, *, time_unit,
                   fusion=_v2.DEFAULT_FUSION, domain=None):
    obs, ref = _convert(observations, reference_time, time_unit)
    result = _v2.compute_lambda(obs, k, ref, computed_at, fusion=fusion, domain=domain)
    result["time_unit"] = time_unit
    result["source_time_unit"] = SOURCE_TIME_UNIT
    return result


# ---------------------------------------------------------------------------
# 2. compute_lambda_for_domain
#    SPEC_V3 §2.2.
# ---------------------------------------------------------------------------
def compute_lambda_for_domain(registry, domain, observations, reference_time, computed_at, *, time_unit):
    obs, ref = _convert(observations, reference_time, time_unit)
    result = _v2.compute_lambda_for_domain(registry, domain, obs, ref, computed_at)
    result["time_unit"] = time_unit
    result["source_time_unit"] = SOURCE_TIME_UNIT
    return result
