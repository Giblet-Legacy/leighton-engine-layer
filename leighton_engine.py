"""
leighton_engine.py — P14 Leighton Engine primitive layer

Function:
    Canonical λ computation from an observation stream. Orchestrates
    P10 (Weight) and P11 (Trust), and returns the complete parameter
    set so any independent implementation can reproduce the result.

Public API:
    1. compute_lambda    — Compute λ with full parameter provenance.
    2. reproduce_lambda  — Recompute λ from the parameter block alone.

Layer:    P14 — Leighton Engine
Depends:  P10 Weight, P11 Trust
Consumed: P15 HAL, P12 Rules, The Cockpit
Version:  1.0.0 (on freeze; 0.0.0-dev until then)
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os
import sys

sys.path.insert(0, os.path.abspath('../weight-layer'))
sys.path.insert(0, os.path.abspath('../trust-layer'))
import weight
import trust

_ALGORITHM = "leighton-engine"
_VERSION = "1.0.0"
_FORMULA = "λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)"

# ---------------------------------------------------------------------------
# 1. compute_lambda
#    Produces λ plus the complete parameter block for reproducibility.
#    Refuses empty streams (unlike P11, which returns 1.0 neutral).
# ---------------------------------------------------------------------------
def compute_lambda(observations, k, reference_time, computed_at):
    if k is None:
        raise ValueError("k (decay constant) must be provided and positive")
    if k <= 0:
        raise ValueError("k (decay constant) must be provided and positive")

    if not observations:
        raise ValueError("observations must not be empty")

    for obs in observations:
        if "timestamp" not in obs:
            raise ValueError("observation missing 'timestamp'")
        if "value" not in obs:
            raise ValueError("observation missing 'value'")

    latest = max(observations, key=lambda o: o["timestamp"])
    latest_time = latest["timestamp"]
    lambda_zero = latest["value"]

    if reference_time < latest_time:
        raise ValueError("reference_time must be >= latest observation timestamp")

    delta_t = reference_time - latest_time
    lam = weight.leighton_weight(lambda_zero, delta_t, k)

    parameters = {
        "algorithm": _ALGORITHM,
        "version": _VERSION,
        "formula": _FORMULA,
        "lambda_zero": lambda_zero,
        "k": k,
        "reference_time": reference_time,
        "latest_observation_timestamp": latest_time,
        "observation_count": len(observations),
        "computed_at": computed_at,
    }

    return {
        "lambda": lam,
        "parameters": parameters,
        "reproducible": True,
    }

# ---------------------------------------------------------------------------
# 2. reproduce_lambda
#    Recomputes λ given only the parameter block from compute_lambda.
#    Raises if algorithm/version mismatch or required keys missing.
# ---------------------------------------------------------------------------
def reproduce_lambda(parameters):
    required = (
        "algorithm", "version", "lambda_zero", "k",
        "reference_time", "latest_observation_timestamp",
    )
    for key in required:
        if key not in parameters:
            raise ValueError(f"parameters missing required key: {key}")

    if parameters["algorithm"] != _ALGORITHM:
        raise ValueError(f"parameters algorithm mismatch: {parameters['algorithm']!r}")
    if parameters["version"] != _VERSION:
        raise ValueError(f"parameters version mismatch: {parameters['version']!r}")

    delta_t = parameters["reference_time"] - parameters["latest_observation_timestamp"]
    return weight.leighton_weight(parameters["lambda_zero"], delta_t, parameters["k"])
