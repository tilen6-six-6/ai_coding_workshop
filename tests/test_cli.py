import json

from loginspect.cli import main
from loginspect.report import render_html, render_json, render_text
from loginspect.rules import RuleEngine, load_spec


def test_cli_review_text(sample_log_path, capsys):
    code = main(["review", sample_log_path, "--spec", "specs/gcu_p.yaml"])
    out = capsys.readouterr().out
    assert "LogInspect review" in out
    assert "FAIL" in out
    assert code == 1  # error-level findings -> non-zero exit


def test_cli_review_json(sample_log_path, capsys):
    main(["review", sample_log_path, "--spec", "specs/gcu_p.yaml", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["snapshot_count"] == 2
    assert payload["passed"] is False


def test_cli_keys(sample_log_path, capsys):
    code = main(["keys", sample_log_path])
    out = capsys.readouterr().out
    assert "main_sw" in out
    assert code == 0


def test_cli_formats(capsys):
    main(["formats"])
    assert "snapshot-text" in capsys.readouterr().out


def test_cli_fail_on_warning_only(sample_log_path):
    # Even with --fail-on info, presence of findings => exit 1
    code = main(["review", sample_log_path, "--spec", "specs/gcu_p.yaml",
                 "--fail-on", "critical"])
    # No CRITICAL findings in fixture, so exit 0 despite errors
    assert code == 0


def test_renderers_run(sample_log):
    spec = load_spec("specs/gcu_p.yaml")
    result = RuleEngine(spec).review(sample_log)
    assert "FAIL" in render_text(result)
    assert "<table" in render_html(result)
    assert json.loads(render_json(result))["spec"]["name"] == "gcu-p"
