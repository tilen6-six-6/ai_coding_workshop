import os

import pytest

from loginspect.model import Severity
from loginspect.rules.checks import check_delta_limit
from loginspect.rules.spec import RuleSpec

TEMPLATES = os.path.join(os.path.dirname(__file__), "..", "templates")
PARAMS = os.path.join(TEMPLATES, "params_GCU-P_260611_7_8_0.xlsm")
WASHTABLE = os.path.join(TEMPLATES, "washtable_GCU-P.xlsx")


def test_delta_limit(sample_log):
    # temperature goes 3698 -> 12000, a jump of 8302
    rule = RuleSpec(id="d", check="delta_limit", severity=Severity.WARNING,
                    key="temperature", params={"max_delta": 1000})
    findings = check_delta_limit(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].snapshot_index == 1


def test_specgen_baseline_rules():
    from loginspect.specgen import baseline_rules

    rules = baseline_rules()
    ids = {r["id"] for r in rules}
    assert "service_status_error" in ids
    assert all("check" in r for r in rules)


def test_specgen_build_without_excel():
    from loginspect.specgen import build_spec

    spec = build_spec(None, None)
    assert spec["name"] == "gcu-p-generated"
    assert len(spec["rules"]) == len(__import__(
        "loginspect.specgen", fromlist=["baseline_rules"]).baseline_rules())


@pytest.mark.skipif(not os.path.exists(PARAMS), reason="template xlsm not present")
def test_specgen_from_performance_sheet():
    from loginspect.specgen import rules_from_performance

    rules = rules_from_performance(PARAMS)
    assert len(rules) > 50  # Performance sheet has many MIN/MAX rows
    for r in rules:
        assert r["check"] == "range"
        assert "min" in r["params"] and "max" in r["params"]


@pytest.mark.skipif(not os.path.exists(PARAMS), reason="template xlsm not present")
def test_specgen_cli_writes_file(tmp_path):
    from loginspect.specgen import main

    out = tmp_path / "gen.yaml"
    code = main(["--params", PARAMS, "--out", str(out)])
    assert code == 0
    assert out.exists()
    text = out.read_text()
    assert "REVIEW BEFORE USE" in text


def test_norm_key():
    from loginspect.specgen import _norm_key

    assert _norm_key("Inlet PW1_1 NormalUS") == "inlet_pw1_1_normalus"
    assert _norm_key("Temp/MW1") == "temp_mw1"
