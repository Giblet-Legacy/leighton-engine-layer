"""
test_leighton_engine.py — P14 Leighton Engine test suite

Function:
    Executable expression of SPEC.md. Written before leighton_engine.py
    per build discipline.

Layer:    P14 — Leighton Engine
Spec:     SPEC.md v1.0.0
Licence:  MSL-1.0
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath('../weight-layer'))
sys.path.insert(0, os.path.abspath('../trust-layer'))

import leighton_engine

def _obs(ts, val):
    return {"timestamp": ts, "value": val}

def test_compute_returns_dict_with_parameters():
    obs = [_obs(0.0, 2.0)]
    result = leighton_engine.compute_lambda(obs, k=0.1, reference_time=10.0, computed_at=1000.0)
    assert "lambda" in result
    assert "parameters" in result
    assert result["reproducible"] is True

def test_compute_parameters_complete():
    obs = [_obs(0.0, 2.0)]
    result = leighton_engine.compute_lambda(obs, k=0.1, reference_time=10.0, computed_at=1000.0)
    p = result["parameters"]
    assert p["algorithm"] == "leighton-engine"
    assert p["version"] == "1.0.0"
    assert p["formula"] == "λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)"
    assert p["lambda_zero"] == 2.0
    assert p["k"] == 0.1
    assert p["reference_time"] == 10.0
    assert p["latest_observation_timestamp"] == 0.0
    assert p["observation_count"] == 1
    assert p["computed_at"] == 1000.0

def test_compute_lambda_matches_manual():
    obs = [_obs(0.0, 0.5)]
    result = leighton_engine.compute_lambda(obs, k=0.2, reference_time=10.0, computed_at=1000.0)
    # λ = 1 + (0.5 − 1) * e^(-0.2 * 10)
    import math
    expected = 1.0 + (0.5 - 1.0) * math.exp(-0.2 * 10)
    assert result["lambda"] == pytest.approx(expected)

def test_reproduce_matches_compute():
    obs = [_obs(0.0, 1.8), _obs(5.0, 0.4)]
    result = leighton_engine.compute_lambda(obs, k=0.15, reference_time=20.0, computed_at=1000.0)
    recomputed = leighton_engine.reproduce_lambda(result["parameters"])
    assert recomputed == pytest.approx(result["lambda"])

def test_reproduce_rejects_wrong_algorithm():
    obs = [_obs(0.0, 1.0)]
    result = leighton_engine.compute_lambda(obs, k=0.1, reference_time=10.0, computed_at=1000.0)
    p = dict(result["parameters"])
    p["algorithm"] = "not-leighton"
    with pytest.raises(ValueError):
        leighton_engine.reproduce_lambda(p)

def test_reproduce_rejects_missing_keys():
    with pytest.raises(ValueError):
        leighton_engine.reproduce_lambda({"algorithm": "leighton-engine"})

def test_empty_observations_rejected():
    with pytest.raises(ValueError):
        leighton_engine.compute_lambda([], k=0.1, reference_time=10.0, computed_at=1000.0)

def test_k_required():
    with pytest.raises(ValueError):
        leighton_engine.compute_lambda([_obs(0.0, 1.0)], k=None, reference_time=10.0, computed_at=1000.0)

def test_reference_time_before_latest():
    with pytest.raises(ValueError):
        leighton_engine.compute_lambda(
            [_obs(100.0, 1.0)], k=0.1, reference_time=50.0, computed_at=1000.0
        )

def test_missing_timestamp():
    with pytest.raises(ValueError):
        leighton_engine.compute_lambda(
            [{"value": 1.0}], k=0.1, reference_time=10.0, computed_at=1000.0
        )

def test_multiple_obs_uses_latest():
    obs = [_obs(0.0, 5.0), _obs(10.0, 0.5)]
    result = leighton_engine.compute_lambda(obs, k=0.1, reference_time=10.0, computed_at=1000.0)
    # latest obs value = 0.5 at t=10; delta = 0 → λ = 0.5
    assert result["lambda"] == pytest.approx(0.5)
    assert result["parameters"]["lambda_zero"] == 0.5
    assert result["parameters"]["latest_observation_timestamp"] == 10.0
    assert result["parameters"]["observation_count"] == 2
