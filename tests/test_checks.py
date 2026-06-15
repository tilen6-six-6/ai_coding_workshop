from loginspect.model import Severity
from loginspect.rules import RuleEngine
from loginspect.rules.checks import (
    check_enum,
    check_forbidden_value,
    check_nonzero_counter,
    check_range,
    check_required_keys,
)
from loginspect.rules.spec import RuleSpec, load_spec


def _rule(check, key=None, severity="warning", **params):
    return RuleSpec(
        id=f"t_{check}", check=check, severity=Severity.from_name(severity),
        key=key, params=params,
    )


def test_range_flags_out_of_bounds(sample_log):
    rule = _rule("range", key="temperature", min=0, max=9000)
    findings = check_range(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].snapshot_index == 1
    assert findings[0].observed == 12000


def test_enum_flags_unknown(sample_log):
    rule = _rule("enum", key="diverter_state", allowed=["POS_0", "POS_1"])
    findings = check_enum(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].observed == "GARBAGE"


def test_forbidden_value(sample_log):
    rule = _rule("forbidden_value", key="service_status", severity="error",
                 values=["ERROR"])
    findings = check_forbidden_value(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR


def test_nonzero_counter_reports_worst(sample_log):
    rule = _rule("nonzero_counter", key="veeprom_error_cntr", threshold=0)
    findings = check_nonzero_counter(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].observed == 2


def test_required_keys_missing(sample_log):
    rule = _rule("required_keys", keys=["main_sw", "does_not_exist"])
    findings = check_required_keys(rule, sample_log)
    assert len(findings) == 1
    assert findings[0].key == "does_not_exist"


def test_engine_full_spec(sample_log):
    spec = load_spec("specs/gcu_p.yaml")
    result = RuleEngine(spec).review(sample_log)
    assert result.snapshot_count == 2
    assert not result.passed  # ERROR-level findings exist
    assert not result.rule_errors
    ids = {f.rule_id for f in result.findings}
    assert "service_status_error" in ids
    assert "veeprom_errors" in ids


def test_engine_findings_sorted_by_severity(sample_log):
    spec = load_spec("specs/gcu_p.yaml")
    result = RuleEngine(spec).review(sample_log)
    sevs = [f.severity for f in result.findings]
    assert sevs == sorted(sevs, reverse=True)


def test_unknown_check_recorded(sample_log):
    bad = RuleSpec(id="oops", check="nope", severity=Severity.INFO)

    class _Bundle:
        name, version, rules = "x", "0", [bad]

    result = RuleEngine(_Bundle()).review(sample_log)
    assert any("unknown check" in e for e in result.rule_errors)
