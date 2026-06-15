from loginspect.aggregate import collapse
from loginspect.rules import RuleEngine
from loginspect.rules.spec import load_spec


def test_collapse_groups_persistent_condition(sample_log):
    spec = load_spec("specs/gcu_p.yaml")
    result = RuleEngine(spec).review(sample_log)
    groups = collapse(result.findings)
    # In the 2-snapshot fixture each rule fires once, so groups == findings,
    # but each group must carry a count and span.
    assert len(groups) == len({(f.rule_id, f.key) for f in result.findings})
    by_id = {g.rule_id: g for g in groups}
    assert by_id["service_status_error"].count == 1


def test_collapse_span_tracking():
    from loginspect.model import Finding, Severity

    findings = [
        Finding("r", Severity.ERROR, "k", "msg", snapshot_index=i,
                raw_timestamp=f"t{i}")
        for i in (5, 2, 9)
    ]
    groups = collapse(findings)
    assert len(groups) == 1
    g = groups[0]
    assert g.count == 3
    assert g.first_index == 2
    assert g.last_index == 9


def test_cli_collapse_flag(sample_log_path, capsys):
    from loginspect.cli import main

    main(["review", sample_log_path, "--spec", "specs/gcu_p.yaml", "--collapse"])
    out = capsys.readouterr().out
    assert "collapsed" in out
    assert "Distinct issues" in out
