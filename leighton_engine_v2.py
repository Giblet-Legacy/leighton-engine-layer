"""
leighton_engine_v2.py — P14 Leighton Engine hardening layer (V2)

Function:
    A layer over leighton_engine.py (v1.0.0, frozen). It does not
    rewrite the primitive. λ is fused by P11 V2 (trust_v2), which
    delegates every decay to P10 (weight_v2 → weight). This layer adds
    multi-observation weighted fusion, a caller-owned domain registry
    for per-domain k, a JSON Schema for the parameters block, and a
    reproduce_lambda that dispatches on version so v1 and V2 parameter
    blocks are both reproducible. Pure: no file writes, no clock reads,
    no module-level mutable state. λ is returned, never stored.

    Gaps in v1 closed here:
      - Two observations sharing the latest timestamp with different
        values gave an order-dependent λ, breaking SPEC §1
        ("same evidence + same parameters MUST produce same λ").
      - NaN/inf in reference_time, timestamp or value returned NaN
        (or 1.0 for reference_time = inf).
      - A non-list observations argument or a non-dict observation
        produced a misleading error.
      - v1 imported P11 but never used it, duplicating its logic.
      - The sibling-layer import paths were resolved against the
        current working directory, not this file.
      - v1 used only the latest observation; the parameter block could
        not carry multi-observation evidence.

Public API:
    1. compute_lambda            — λ with full provenance (weighted or latest)
    2. reproduce_lambda          — recompute λ from a v1 or V2 parameter block
    3. validate_parameters       — check a V2 parameter block (schema + cross-field)
    4. load_parameters_schema    — the JSON Schema for a V2 parameter block
    5. DomainRegistry            — caller-owned name → (k, fusion) map
    6. compute_lambda_for_domain — compute_lambda using a registered domain

Layer:    P14 — Leighton Engine
Depends:  leighton_engine.py (P14 v1.0.0), trust_v2.py (P11 v1.1.0),
          weight_v2.py (P10 v1.1.0)
Consumed: P15 HAL, P12 Rules, The Cockpit
Version:  1.1.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _name in ("trust-layer", "weight-layer"):
    _path = os.path.normpath(os.path.join(_HERE, "..", _name))
    if _path not in sys.path:
        sys.path.insert(0, _path)

import trust_v2  # noqa: E402
import weight_v2  # noqa: E402

import leighton_engine  # noqa: E402

ALGORITHM = "leighton-engine"
VERSION = "1.1.0"
FORMULA = leighton_engine._FORMULA
FUSION_RULES = ("weighted", "latest")
FUSION_FORMULAS = {
    "weighted": "λ = 1.00 + Σ wᵢ(λᵢ − 1.00) / Σ wᵢ, wᵢ = cᵢ × e^(−kΔtᵢ)",
    "latest": "λ₀ = value of the latest observation",
}
DEFAULT_FUSION = "weighted"
DEFAULT_CONFIDENCE = trust_v2.DEFAULT_CONFIDENCE
SCHEMA_PATH = os.path.join(_HERE, "leighton_parameters_v2.schema.json")

_REQUIRED_KEYS = (
    "algorithm", "version", "formula", "fusion_rule", "fusion_formula",
    "k", "reference_time", "latest_observation_timestamp",
    "observation_count", "computed_at", "domain", "observations",
)
_OBSERVATION_KEYS = ("timestamp", "value", "confidence")


# ---------------------------------------------------------------------------
# 1. _is_number (internal)
#    True for a real int or float. bool is rejected, as in P10/P11 V2.
# ---------------------------------------------------------------------------
def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# 2. _check_finite (internal)
#    TypeError for a non-number, ValueError for NaN/inf. The name is
#    used in the message so the caller can find the bad field.
# ---------------------------------------------------------------------------
def _check_finite(name, value):
    if not _is_number(value):
        raise TypeError(name + " must be a number")
    if not math.isfinite(value):
        raise ValueError(name + " must be finite (got " + repr(value) + ")")


# ---------------------------------------------------------------------------
# 3. _check_fusion (internal)
#    Rejects an unknown fusion rule name.
# ---------------------------------------------------------------------------
def _check_fusion(fusion):
    if fusion not in FUSION_RULES:
        raise ValueError(
            "fusion must be one of " + repr(FUSION_RULES) + " (got " + repr(fusion) + ")"
        )


# ---------------------------------------------------------------------------
# 4. _check_domain (internal)
#    A domain is None or a non-empty string.
# ---------------------------------------------------------------------------
def _check_domain(domain):
    if domain is None:
        return
    if not isinstance(domain, str):
        raise TypeError("domain must be a string or None")
    if not domain:
        raise ValueError("domain must not be an empty string")


# ---------------------------------------------------------------------------
# 5. _canonical (internal)
#    Returns the observations as new dicts with exactly timestamp,
#    value and confidence (default filled in), sorted by
#    (timestamp, value, confidence). Fusing this list makes λ
#    bit-identical regardless of input order, and storing it makes the
#    evidence part of the parameter block. Call only after validation.
# ---------------------------------------------------------------------------
def _canonical(observations):
    rows = [
        {
            "timestamp": obs["timestamp"],
            "value": obs["value"],
            "confidence": obs.get("confidence", DEFAULT_CONFIDENCE),
        }
        for obs in observations
    ]
    rows.sort(key=lambda r: (r["timestamp"], r["value"], r["confidence"]))
    return rows


# ---------------------------------------------------------------------------
# 6. _fuse (internal)
#    Runs one fusion rule over an already-canonical observation list
#    via P11 V2. Returns (lambda, fallback). fallback is P11 V2's
#    neutral-fallback reason for the weighted rule, None otherwise.
# ---------------------------------------------------------------------------
def _fuse(fusion, observations, k, reference_time):
    if fusion == "weighted":
        info = trust_v2.explain_lambda(observations, k, reference_time)
        return info["lambda"], info["fallback"]
    return trust_v2.calculate_lambda_latest(observations, k, reference_time), None


# ---------------------------------------------------------------------------
# 7. compute_lambda
#    Canonical λ with full provenance. fusion="weighted" (default)
#    fuses every observation by freshness × confidence; fusion="latest"
#    is the v1 rule, hardened (ambiguous latest evidence rejected).
#    Validation order: fusion, domain, then P11 V2 (k, reference_time,
#    observations, each observation), then empty stream, then
#    computed_at. Refuses an empty stream (as v1) and, for weighted
#    fusion, a stream whose every confidence is 0 — both would hide
#    that the caller supplied no usable evidence. Evidence fully
#    decayed past float precision is a real answer (neutral) and is
#    returned with fallback="fully_decayed". Inputs are never mutated.
# ---------------------------------------------------------------------------
def compute_lambda(observations, k, reference_time, computed_at,
                   fusion=DEFAULT_FUSION, domain=None):
    _check_fusion(fusion)
    _check_domain(domain)

    # P11 V2 validates k, reference_time and each observation (with
    # its input index in the message) before anything is reordered.
    trust_v2.calculate_lambda(observations, k, reference_time)

    if not observations:
        raise ValueError("observations must not be empty")
    _check_finite("computed_at", computed_at)

    canonical = _canonical(observations)
    lam, fallback = _fuse(fusion, canonical, k, reference_time)
    if fallback == "no_confidence":
        raise ValueError("every observation has confidence 0; no usable evidence")

    parameters = {
        "algorithm": ALGORITHM,
        "version": VERSION,
        "formula": FORMULA,
        "fusion_rule": fusion,
        "fusion_formula": FUSION_FORMULAS[fusion],
        "k": k,
        "reference_time": reference_time,
        "latest_observation_timestamp": canonical[-1]["timestamp"],
        "observation_count": len(canonical),
        "computed_at": computed_at,
        "domain": domain,
        "observations": canonical,
    }

    return {
        "lambda": lam,
        "parameters": parameters,
        "reproducible": True,
        "fallback": fallback,
    }


# ---------------------------------------------------------------------------
# 8. validate_parameters
#    Checks a V2 parameter block: every rule in
#    leighton_parameters_v2.schema.json, plus finiteness (JSON cannot
#    carry NaN/inf but Python can) and the cross-field rules a schema
#    cannot express. Raises ValueError (or TypeError for a non-dict)
#    naming the first failure; returns None when valid.
# ---------------------------------------------------------------------------
def validate_parameters(parameters):
    if not isinstance(parameters, dict):
        raise TypeError("parameters must be a dict")
    for key in _REQUIRED_KEYS:
        if key not in parameters:
            raise ValueError("parameters missing required key: " + key)
    extra = sorted(set(parameters) - set(_REQUIRED_KEYS))
    if extra:
        raise ValueError("parameters has unknown keys: " + repr(extra))

    p = parameters
    if p["algorithm"] != ALGORITHM:
        raise ValueError("parameters algorithm mismatch: " + repr(p["algorithm"]))
    if p["version"] != VERSION:
        raise ValueError("parameters version mismatch: " + repr(p["version"]))
    if p["formula"] != FORMULA:
        raise ValueError("parameters formula mismatch: " + repr(p["formula"]))
    if p["fusion_rule"] not in FUSION_RULES:
        raise ValueError("parameters fusion_rule unknown: " + repr(p["fusion_rule"]))
    if p["fusion_formula"] != FUSION_FORMULAS[p["fusion_rule"]]:
        raise ValueError("parameters fusion_formula does not match fusion_rule")

    for key in ("k", "reference_time", "latest_observation_timestamp", "computed_at"):
        try:
            _check_finite(key, p[key])
        except TypeError as exc:
            raise ValueError("parameters " + str(exc)) from exc
    if not (weight_v2.K_MIN <= p["k"] <= weight_v2.K_MAX):
        raise ValueError("parameters k out of bounds: " + repr(p["k"]))

    count = p["observation_count"]
    if (not _is_number(count) or not math.isfinite(count)
            or count != int(count) or count < 1):
        raise ValueError("parameters observation_count must be an integer >= 1")

    domain = p["domain"]
    if domain is not None and (not isinstance(domain, str) or not domain):
        raise ValueError("parameters domain must be null or a non-empty string")

    obs_list = p["observations"]
    if not isinstance(obs_list, list) or not obs_list:
        raise ValueError("parameters observations must be a non-empty list")
    for i, obs in enumerate(obs_list):
        where = "parameters observations[" + str(i) + "]"
        if not isinstance(obs, dict) or set(obs) != set(_OBSERVATION_KEYS):
            raise ValueError(where + " must have exactly " + repr(_OBSERVATION_KEYS))
        for key in _OBSERVATION_KEYS:
            try:
                _check_finite(where + "." + key, obs[key])
            except TypeError as exc:
                raise ValueError(str(exc)) from exc
        if obs["value"] <= 0:
            raise ValueError(where + ".value must be positive")
        if not (0.0 <= obs["confidence"] <= 1.0):
            raise ValueError(where + ".confidence must be in [0, 1]")

    if count != len(obs_list):
        raise ValueError("parameters observation_count does not match observations")
    latest = max(obs["timestamp"] for obs in obs_list)
    if p["latest_observation_timestamp"] != latest:
        raise ValueError(
            "parameters latest_observation_timestamp does not match observations"
        )


# ---------------------------------------------------------------------------
# 9. reproduce_lambda
#    Recomputes λ from a parameter block alone, dispatching on version:
#    "1.0.0" → frozen v1 leighton_engine.reproduce_lambda;
#    "1.1.0" → validate_parameters, then the stored fusion rule over
#    the stored (canonical) observations. Works on a block that has
#    been through a JSON round trip. Any other version → ValueError.
# ---------------------------------------------------------------------------
def reproduce_lambda(parameters):
    if not isinstance(parameters, dict):
        raise TypeError("parameters must be a dict")
    version = parameters.get("version")
    if version == leighton_engine._VERSION:
        return leighton_engine.reproduce_lambda(parameters)
    if version != VERSION:
        raise ValueError("parameters version unsupported: " + repr(version))

    validate_parameters(parameters)
    observations = _canonical(parameters["observations"])
    lam, fallback = _fuse(
        parameters["fusion_rule"], observations,
        parameters["k"], parameters["reference_time"],
    )
    if fallback == "no_confidence":
        raise ValueError("every observation has confidence 0; no usable evidence")
    return lam


# ---------------------------------------------------------------------------
# 10. load_parameters_schema
#     Reads and returns the JSON Schema shipped beside this file.
#     Read-only; the only file access in this layer.
# ---------------------------------------------------------------------------
def load_parameters_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# 11. DomainRegistry
#     Caller-owned map of domain name → {"k", "fusion"}. Registration
#     follows the Immutable Rule: re-registering a name with the same
#     configuration is a no-op; with a different one is a ValueError.
#     There is no unregister and no module-level default instance.
# ---------------------------------------------------------------------------
class DomainRegistry:

    # 11.1 __init__ — start empty.
    def __init__(self):
        self._domains = {}

    # 11.2 register — validate and add one domain; returns its config.
    def register(self, name, k, fusion=DEFAULT_FUSION):
        _check_domain(name)
        if name is None:
            raise TypeError("domain name must be a string")
        _check_fusion(fusion)
        if k is None:
            raise ValueError("k (decay constant) must be provided explicitly")
        weight_v2.leighton_weight(weight_v2.NEUTRAL, 0.0, k)

        config = {"k": k, "fusion": fusion}
        existing = self._domains.get(name)
        if existing is not None and existing != config:
            raise ValueError(
                "domain " + repr(name) + " already registered with " + repr(existing)
            )
        self._domains[name] = config
        return dict(config)

    # 11.3 get — a copy of one domain's config; KeyError if unknown.
    def get(self, name):
        if name not in self._domains:
            raise KeyError("unknown domain: " + repr(name))
        return dict(self._domains[name])

    # 11.4 names — registered names, sorted.
    def names(self):
        return sorted(self._domains)

    # 11.5 __contains__ — `name in registry`.
    def __contains__(self, name):
        return name in self._domains

    # 11.6 __len__ — number of registered domains.
    def __len__(self):
        return len(self._domains)


# ---------------------------------------------------------------------------
# 12. compute_lambda_for_domain
#     compute_lambda with k and fusion taken from a registered domain.
#     The domain name is recorded in the parameter block; k is stored
#     too, so reproduce_lambda never needs the registry.
# ---------------------------------------------------------------------------
def compute_lambda_for_domain(registry, domain, observations, reference_time, computed_at):
    if not isinstance(registry, DomainRegistry):
        raise TypeError("registry must be a DomainRegistry")
    config = registry.get(domain)
    return compute_lambda(
        observations, config["k"], reference_time, computed_at,
        fusion=config["fusion"], domain=domain,
    )
