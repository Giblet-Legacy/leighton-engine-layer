"""
test_leighton_engine_v2.py — P14 Leighton Engine V2 test suite

Function:
    Executable expression of SPEC_V2.md. Covers weighted and latest
    fusion, order independence, the reproducibility invariant (including
    after a JSON round trip), validation, the parameter JSON Schema and
    the domain registry. v1 tests (test_leighton_engine.py) are frozen
    and still run alongside this file.

Layer:    P14 — Leighton Engine
Spec:     SPEC_V2.md 1.1.0
Licence:  MSL-1.0
"""

import copy
import itertools
import json
import math

import pytest

import leighton_engine
import leighton_engine_v2 as le2
import trust_v2


# ---------------------------------------------------------------------------
# 1. Helpers
# ---------------------------------------------------------------------------
def _obs(ts, val, conf=None):
    o = {"timestamp": ts, "value": val}
    if conf is not None:
        o["confidence"] = conf
    return o


STREAM = [_obs(0.0, 1.8), _obs(5.0, 0.4, 0.5), _obs(12.0, 1.3)]


def _compute(obs=None, k=0.15, ref=20.0, at=1000.0, **kw):
    return le2.compute_lambda(STREAM if obs is None else obs, k, ref, at, **kw)


# ---------------------------------------------------------------------------
# 2. Result shape and parameter block
# ---------------------------------------------------------------------------
def test_result_keys():
    r = _compute()
    assert set(r) == {"lambda", "parameters", "reproducible", "fallback"}
    assert r["reproducible"] is True
    assert r["fallback"] is None


def test_parameters_complete():
    p = _compute(domain="ops")["parameters"]
    assert p["algorithm"] == "leighton-engine"
    assert p["version"] == "1.1.0"
    assert p["formula"] == leighton_engine._FORMULA
    assert p["fusion_rule"] == "weighted"
    assert p["fusion_formula"] == le2.FUSION_FORMULAS["weighted"]
    assert p["k"] == 0.15
    assert p["reference_time"] == 20.0
    assert p["latest_observation_timestamp"] == 12.0
    assert p["observation_count"] == 3
    assert p["computed_at"] == 1000.0
    assert p["domain"] == "ops"
    assert p["observations"] == [
        {"timestamp": 0.0, "value": 1.8, "confidence": 1.0},
        {"timestamp": 5.0, "value": 0.4, "confidence": 0.5},
        {"timestamp": 12.0, "value": 1.3, "confidence": 1.0},
    ]


def test_default_domain_is_none():
    assert _compute()["parameters"]["domain"] is None


def test_inputs_not_mutated():
    obs = [_obs(5.0, 0.4), _obs(0.0, 1.8, 0.3)]
    snapshot = copy.deepcopy(obs)
    r = _compute(obs)
    assert obs == snapshot
    r["parameters"]["observations"][0]["value"] = 99.0
    assert obs == snapshot


def test_extra_observation_keys_dropped():
    p = _compute([_obs(0.0, 2.0) | {"source": "x"}])["parameters"]
    assert p["observations"] == [{"timestamp": 0.0, "value": 2.0, "confidence": 1.0}]


# ---------------------------------------------------------------------------
# 3. Weighted fusion
# ---------------------------------------------------------------------------
def test_weighted_matches_p11_v2():
    assert _compute()["lambda"] == pytest.approx(
        trust_v2.calculate_lambda(STREAM, 0.15, 20.0)
    )


def test_weighted_matches_manual_formula():
    k, ref = 0.15, 20.0
    num = den = 0.0
    for o in STREAM:
        dt = ref - o["timestamp"]
        f = math.exp(-k * dt)
        w = o.get("confidence", 1.0) * f
        num += w * (o["value"] - 1.0) * f
        den += w
    assert _compute()["lambda"] == pytest.approx(1.0 + num / den)


def test_single_observation_weighted_equals_v1():
    obs = [_obs(0.0, 0.5)]
    v1 = leighton_engine.compute_lambda(obs, 0.2, 10.0, 1000.0)["lambda"]
    assert _compute(obs, k=0.2, ref=10.0)["lambda"] == pytest.approx(v1)


def test_weighted_differs_from_latest_with_multiple_obs():
    assert _compute()["lambda"] != pytest.approx(_compute(fusion="latest")["lambda"])


@pytest.mark.parametrize("perm", list(itertools.permutations(range(3))))
def test_weighted_order_independent_bitwise(perm):
    obs = [STREAM[i] for i in perm]
    r = _compute(obs)
    base = _compute()
    assert r["lambda"] == base["lambda"]
    assert r["parameters"] == base["parameters"]


def test_tied_latest_order_independent():
    a = [_obs(0.0, 2.0), _obs(0.0, 0.5)]
    assert _compute(a, ref=10.0)["lambda"] == _compute(a[::-1], ref=10.0)["lambda"]


def test_fully_decayed_returns_neutral_with_fallback():
    r = _compute([_obs(0.0, 2.0)], k=1.0, ref=1e6)
    assert r["lambda"] == 1.0
    assert r["fallback"] == "fully_decayed"
    assert le2.reproduce_lambda(r["parameters"]) == 1.0


def test_zero_confidence_everywhere_refused():
    with pytest.raises(ValueError, match="confidence 0"):
        _compute([_obs(0.0, 2.0, 0.0), _obs(1.0, 0.5, 0.0)])


def test_some_zero_confidence_allowed():
    r = _compute([_obs(0.0, 2.0, 0.0), _obs(1.0, 0.5)], ref=1.0)
    assert r["lambda"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# 4. Latest fusion
# ---------------------------------------------------------------------------
def test_latest_matches_v1():
    v1 = leighton_engine.compute_lambda(STREAM, 0.15, 20.0, 1000.0)["lambda"]
    r = _compute(fusion="latest")
    assert r["lambda"] == pytest.approx(v1)
    assert r["fallback"] is None
    assert r["parameters"]["fusion_formula"] == le2.FUSION_FORMULAS["latest"]


def test_latest_ambiguous_rejected():
    with pytest.raises(ValueError, match="ambiguous"):
        _compute([_obs(0.0, 2.0), _obs(0.0, 0.5)], ref=10.0, fusion="latest")


def test_latest_identical_tie_allowed():
    r = _compute([_obs(0.0, 2.0), _obs(0.0, 2.0)], ref=0.0, fusion="latest")
    assert r["lambda"] == pytest.approx(2.0)


def test_latest_ignores_zero_confidence():
    r = _compute([_obs(0.0, 2.0, 0.0)], ref=0.0, fusion="latest")
    assert r["lambda"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 5. Reproducibility invariant
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fusion", le2.FUSION_RULES)
def test_reproduce_exact(fusion):
    r = _compute(fusion=fusion)
    assert le2.reproduce_lambda(r["parameters"]) == r["lambda"]


@pytest.mark.parametrize("fusion", le2.FUSION_RULES)
def test_reproduce_after_json_round_trip(fusion):
    r = _compute([_obs(3, 2), _obs(1, 0.25, 0.75)], k=0.05, ref=7, fusion=fusion)
    p = json.loads(json.dumps(r["parameters"]))
    assert le2.reproduce_lambda(p) == r["lambda"]


def test_reproduce_dispatches_v1_block():
    r = leighton_engine.compute_lambda([_obs(0.0, 1.8), _obs(5.0, 0.4)], 0.15, 20.0, 1000.0)
    assert le2.reproduce_lambda(r["parameters"]) == r["lambda"]


def test_reproduce_unknown_version():
    p = _compute()["parameters"]
    p["version"] = "9.9.9"
    with pytest.raises(ValueError, match="unsupported"):
        le2.reproduce_lambda(p)


def test_reproduce_not_dict():
    with pytest.raises(TypeError):
        le2.reproduce_lambda([1, 2])


def test_reproduce_rejects_tampered_count():
    p = _compute()["parameters"]
    p["observation_count"] = 2
    with pytest.raises(ValueError, match="observation_count"):
        le2.reproduce_lambda(p)


def test_reproduce_rejects_tampered_latest():
    p = _compute()["parameters"]
    p["latest_observation_timestamp"] = 11.0
    with pytest.raises(ValueError, match="latest_observation_timestamp"):
        le2.reproduce_lambda(p)


# ---------------------------------------------------------------------------
# 6. Input validation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kwargs, exc", [
    ({"k": None}, ValueError),
    ({"k": 0}, ValueError),
    ({"k": -1}, ValueError),
    ({"k": True}, TypeError),
    ({"k": "0.1"}, TypeError),
    ({"k": float("nan")}, ValueError),
    ({"k": 1e-12}, ValueError),
    ({"ref": float("inf")}, ValueError),
    ({"ref": float("nan")}, ValueError),
    ({"ref": "10"}, TypeError),
    ({"ref": 5.0}, ValueError),
    ({"at": None}, TypeError),
    ({"at": float("nan")}, ValueError),
    ({"fusion": "mean"}, ValueError),
    ({"domain": ""}, ValueError),
    ({"domain": 7}, TypeError),
])
def test_bad_arguments(kwargs, exc):
    with pytest.raises(exc):
        _compute(**kwargs)


@pytest.mark.parametrize("obs, exc", [
    ([], ValueError),
    ("abc", TypeError),
    ([1.0], TypeError),
    ([{"value": 1.0}], ValueError),
    ([{"timestamp": 0.0}], ValueError),
    ([_obs(0.0, float("nan"))], ValueError),
    ([_obs(float("nan"), 1.0)], ValueError),
    ([_obs(0.0, 0.0)], ValueError),
    ([_obs(0.0, -1.0)], ValueError),
    ([_obs(0.0, 1.0, 1.5)], ValueError),
    ([_obs(0.0, 1.0, "high")], TypeError),
])
def test_bad_observations(obs, exc):
    with pytest.raises(exc):
        _compute(obs)


def test_bad_observation_message_names_index():
    with pytest.raises(ValueError, match=r"observations\[1\]"):
        _compute([_obs(0.0, 1.0), _obs(1.0, float("nan"))])


def test_empty_checked_after_k():
    with pytest.raises(ValueError, match="k"):
        _compute([], k=-1)


def test_tuple_observations_accepted():
    assert _compute(tuple(STREAM))["lambda"] == _compute()["lambda"]


# ---------------------------------------------------------------------------
# 7. Parameter schema
# ---------------------------------------------------------------------------
def test_schema_loads_and_matches_required_keys():
    schema = le2.load_parameters_schema()
    assert set(schema["required"]) == set(le2._REQUIRED_KEYS)
    assert set(schema["properties"]) == set(le2._REQUIRED_KEYS)
    assert schema["properties"]["version"]["const"] == le2.VERSION
    assert schema["properties"]["formula"]["const"] == le2.FORMULA
    assert set(schema["properties"]["fusion_rule"]["enum"]) == set(le2.FUSION_RULES)
    assert set(schema["properties"]["fusion_formula"]["enum"]) == set(
        le2.FUSION_FORMULAS.values()
    )


def _mutations():
    base = _compute(domain="ops")["parameters"]

    def m(fn):
        p = copy.deepcopy(base)
        fn(p)
        return p

    return [
        m(lambda p: p.pop("k")),
        m(lambda p: p.update(extra=1)),
        m(lambda p: p.update(algorithm="other")),
        m(lambda p: p.update(version="1.0.0")),
        m(lambda p: p.update(formula="x")),
        m(lambda p: p.update(fusion_rule="mean")),
        m(lambda p: p.update(k=0)),
        m(lambda p: p.update(k=1e10)),
        m(lambda p: p.update(k="0.1")),
        m(lambda p: p.update(reference_time=True)),
        m(lambda p: p.update(observation_count=0)),
        m(lambda p: p.update(domain="")),
        m(lambda p: p.update(domain=3)),
        m(lambda p: p.update(observations=[])),
        m(lambda p: p["observations"][0].pop("confidence")),
        m(lambda p: p["observations"][0].update(source="x")),
        m(lambda p: p["observations"][0].update(value=0)),
        m(lambda p: p["observations"][0].update(confidence=2)),
    ]


def test_validate_accepts_valid():
    for fusion in le2.FUSION_RULES:
        assert le2.validate_parameters(_compute(fusion=fusion)["parameters"]) is None


@pytest.mark.parametrize("bad", _mutations())
def test_validate_rejects_schema_violations(bad):
    with pytest.raises(ValueError):
        le2.validate_parameters(bad)


def test_validate_rejects_mismatched_fusion_formula():
    p = _compute()["parameters"]
    p["fusion_formula"] = le2.FUSION_FORMULAS["latest"]
    with pytest.raises(ValueError, match="fusion_formula"):
        le2.validate_parameters(p)


def test_validate_rejects_nan():
    p = _compute()["parameters"]
    p["computed_at"] = float("nan")
    with pytest.raises(ValueError):
        le2.validate_parameters(p)


def test_jsonschema_agrees_with_validator():
    jsonschema = pytest.importorskip("jsonschema")
    schema = le2.load_parameters_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for fusion in le2.FUSION_RULES:
        p = json.loads(json.dumps(_compute(fusion=fusion, domain="d")["parameters"]))
        assert not list(validator.iter_errors(p))
    for bad in _mutations():
        assert list(validator.iter_errors(json.loads(json.dumps(bad))))


# ---------------------------------------------------------------------------
# 8. Domain registry
# ---------------------------------------------------------------------------
def test_registry_register_and_get():
    reg = le2.DomainRegistry()
    assert reg.register("ops", 0.1) == {"k": 0.1, "fusion": "weighted"}
    reg.register("sec", 0.5, fusion="latest")
    assert reg.get("sec") == {"k": 0.5, "fusion": "latest"}
    assert reg.names() == ["ops", "sec"]
    assert "ops" in reg and "x" not in reg
    assert len(reg) == 2


def test_registry_get_returns_copy():
    reg = le2.DomainRegistry()
    reg.register("ops", 0.1)
    reg.get("ops")["k"] = 9.0
    assert reg.get("ops")["k"] == 0.1


def test_registry_same_config_is_noop():
    reg = le2.DomainRegistry()
    reg.register("ops", 0.1)
    reg.register("ops", 0.1)
    assert len(reg) == 1


def test_registry_conflict_rejected():
    reg = le2.DomainRegistry()
    reg.register("ops", 0.1)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("ops", 0.2)
    assert reg.get("ops")["k"] == 0.1


@pytest.mark.parametrize("name, k, fusion, exc", [
    (None, 0.1, "weighted", TypeError),
    ("", 0.1, "weighted", ValueError),
    (5, 0.1, "weighted", TypeError),
    ("a", None, "weighted", ValueError),
    ("a", 0, "weighted", ValueError),
    ("a", float("inf"), "weighted", ValueError),
    ("a", True, "weighted", TypeError),
    ("a", 0.1, "mean", ValueError),
])
def test_registry_rejects_bad(name, k, fusion, exc):
    with pytest.raises(exc):
        le2.DomainRegistry().register(name, k, fusion)


def test_registries_are_independent():
    a, b = le2.DomainRegistry(), le2.DomainRegistry()
    a.register("ops", 0.1)
    assert "ops" not in b


def test_compute_for_domain():
    reg = le2.DomainRegistry()
    reg.register("sec", 0.5, fusion="latest")
    r = le2.compute_lambda_for_domain(reg, "sec", STREAM, 20.0, 1000.0)
    direct = _compute(k=0.5, fusion="latest", domain="sec")
    assert r == direct
    assert le2.reproduce_lambda(r["parameters"]) == r["lambda"]


def test_compute_for_unknown_domain():
    with pytest.raises(KeyError):
        le2.compute_lambda_for_domain(le2.DomainRegistry(), "x", STREAM, 20.0, 1000.0)


def test_compute_for_domain_needs_registry():
    with pytest.raises(TypeError):
        le2.compute_lambda_for_domain({"x": 0.1}, "x", STREAM, 20.0, 1000.0)
