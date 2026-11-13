"""
test_leighton_engine_v3.py — P14 Leighton Engine V3 (time-unit layer) test suite

Function:
    Executable expression of SPEC_V3.md. Written before
    leighton_engine_v3.py and run red first.

Functions in this file (pytest-collected):
    1. test_public_api
    2. test_time_unit_required
    3. test_seconds_equals_v2
    4. test_days_equals_v2_on_converted
    5. test_weaver_anchor_and_old_cockpit_call
    6. test_result_records_units_and_reproduces
    7. test_bad_time_types
    8. test_no_mutation
    9. test_stack_constants
    10. test_domain_call

Layer:    P14 — Leighton Engine, V3
Spec:     SPEC_V3.md 1.2.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import copy

import pytest

import leighton_engine_v2 as v2
import leighton_engine_v3 as v3

DAY = 86400.0
T0 = 1_700_000_000.0
OBS = [{"timestamp": T0, "value": 1.5}, {"timestamp": T0 + 2 * DAY, "value": 1.2, "confidence": 0.5}]


# 1. test_public_api
def test_public_api():
    for name in ("compute_lambda", "compute_lambda_for_domain", "reproduce_lambda",
                 "validate_parameters", "load_parameters_schema", "DomainRegistry"):
        assert callable(getattr(v3, name))
    assert v3.reproduce_lambda is v2.reproduce_lambda


# 2. test_time_unit_required
def test_time_unit_required():
    with pytest.raises(TypeError):
        v3.compute_lambda(OBS, 0.1, T0 + 5 * DAY, T0)
    with pytest.raises(ValueError):
        v3.compute_lambda(OBS, 0.1, T0 + 5 * DAY, T0, time_unit="weeks")


# 3. test_seconds_equals_v2
def test_seconds_equals_v2():
    a = v3.compute_lambda(OBS, 1e-6, T0 + 5 * DAY, T0, time_unit="seconds")
    b = v2.compute_lambda(OBS, 1e-6, T0 + 5 * DAY, T0)
    assert a["lambda"] == b["lambda"] and a["parameters"] == b["parameters"]


# 4. test_days_equals_v2_on_converted
def test_days_equals_v2_on_converted():
    conv = [dict(o, timestamp=o["timestamp"] / DAY) for o in OBS]
    a = v3.compute_lambda(OBS, 0.1, T0 + 5 * DAY, T0, time_unit="days")
    b = v2.compute_lambda(conv, 0.1, (T0 + 5 * DAY) / DAY, T0)
    assert a["lambda"] == b["lambda"] and a["parameters"] == b["parameters"]


# 5. test_weaver_anchor_and_old_cockpit_call
def test_weaver_anchor_and_old_cockpit_call():
    r = v3.compute_lambda([{"timestamp": T0, "value": 1.5}], 0.1, T0 + 10 * DAY, T0, time_unit="days")
    assert r["lambda"] == pytest.approx(1.1839, abs=1e-4)
    old = v2.compute_lambda([{"timestamp": 0.0, "value": 1.5}], 0.1, T0, T0)
    assert old["lambda"] == 1.0  # the forge trust defect: k per second over 54 years


# 6. test_result_records_units_and_reproduces
def test_result_records_units_and_reproduces():
    r = v3.compute_lambda(OBS, 0.1, T0 + 5 * DAY, T0, time_unit="days")
    assert r["time_unit"] == "days" and r["source_time_unit"] == "seconds"
    v2.validate_parameters(r["parameters"])
    assert v2.reproduce_lambda(r["parameters"]) == r["lambda"]


# 7. test_bad_time_types
def test_bad_time_types():
    for bad in (True, "1", None):
        with pytest.raises(TypeError):
            v3.compute_lambda([{"timestamp": bad, "value": 1.5}], 0.1, T0, T0, time_unit="days")
        with pytest.raises(TypeError):
            v3.compute_lambda(OBS, 0.1, bad, T0, time_unit="days")


# 8. test_no_mutation
def test_no_mutation():
    obs = copy.deepcopy(OBS)
    v3.compute_lambda(obs, 0.1, T0 + 5 * DAY, T0, time_unit="hours")
    assert obs == OBS


# 9. test_stack_constants
def test_stack_constants():
    assert v3.STACK_TIME_UNIT == "days" and v3.STACK_CLAIM_K == 0.1


# 10. test_domain_call
def test_domain_call():
    reg = v3.DomainRegistry()
    reg.register("claims", 0.1)
    r = v3.compute_lambda_for_domain(reg, "claims", OBS, T0 + 5 * DAY, T0, time_unit="days")
    assert r["parameters"]["domain"] == "claims" and r["time_unit"] == "days"
