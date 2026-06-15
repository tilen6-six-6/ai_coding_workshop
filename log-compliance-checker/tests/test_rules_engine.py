"""Tests for the rules engine and parser. Run: python -m pytest -q  (or python tests/test_rules_engine.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import parse_text, parse_line       # noqa: E402
from src.rules_engine import evaluate               # noqa: E402


def _rules(rule):
    return {"rules": [rule]}


def test_parse_json_line():
    e = parse_line(1, '{"level":"INFO","code":200}')
    assert e.get("level") == "INFO"
    assert e.get("code") == 200


def test_parse_kv_line():
    e = parse_line(1, 'level=ERROR code=500 msg="boom"')
    assert e.get("level") == "ERROR"
    assert e.get("code") == 500
    assert e.get("msg") == "boom"


def test_parse_syslog():
    e = parse_line(1, "Jun 15 10:00:01 host app[42]: started")
    assert e.get("app") == "app"
    assert e.get("pid") == 42
    assert "started" in e.get("message")


def test_required_fields():
    entries = parse_text('{"level":"INFO"}')
    r = evaluate(_rules({"id": "R", "type": "required_fields",
                         "fields": ["level", "message"]}), entries)
    assert len(r.issues) == 1
    assert "message" in r.issues[0].message


def test_allowed_values():
    entries = parse_text('{"level":"TRACE"}')
    r = evaluate(_rules({"id": "R", "type": "allowed_values", "field": "level",
                         "allowed": ["INFO", "ERROR"]}), entries)
    assert len(r.issues) == 1


def test_range():
    entries = parse_text('{"temp_c":97}')
    r = evaluate(_rules({"id": "R", "type": "range", "field": "temp_c",
                         "min": 0, "max": 85, "severity": "critical"}), entries)
    assert len(r.issues) == 1
    assert r.issues[0].severity == "critical"
    assert not r.passed


def test_forbidden_pattern():
    entries = parse_text('{"message":"password=hunter2"}')
    r = evaluate(_rules({"id": "R", "type": "forbidden_pattern",
                         "pattern": r"password\s*=\s*\S+"}), entries)
    assert len(r.issues) == 1


def test_must_occur():
    entries = parse_text('{"event":"other"}')
    r = evaluate(_rules({"id": "R", "type": "must_occur",
                         "match": {"event": "startup"}, "count": 1}), entries)
    assert len(r.issues) == 1


def test_must_not_occur():
    entries = parse_text('{"event":"unauthorized_access"}')
    r = evaluate(_rules({"id": "R", "type": "must_not_occur",
                         "match": {"event": "unauthorized_access"},
                         "max_count": 0}), entries)
    assert len(r.issues) == 1


def test_ordering_wrong_order():
    entries = parse_text(
        '{"event":"resource_access"}\n{"event":"auth_ok"}'
    )
    r = evaluate(_rules({"id": "R", "type": "ordering",
                         "before": {"event": "auth_ok"},
                         "after": {"event": "resource_access"}}), entries)
    assert len(r.issues) == 1


def test_ordering_correct_order_passes():
    entries = parse_text(
        '{"event":"auth_ok"}\n{"event":"resource_access"}'
    )
    r = evaluate(_rules({"id": "R", "type": "ordering",
                         "before": {"event": "auth_ok"},
                         "after": {"event": "resource_access"}}), entries)
    assert len(r.issues) == 0


def test_when_filter_scopes_rule():
    entries = parse_text('{"env":"dev","level":"BAD"}\n{"env":"prod","level":"BAD"}')
    r = evaluate(_rules({"id": "R", "type": "allowed_values", "field": "level",
                         "allowed": ["INFO"], "when": {"env": "prod"}}), entries)
    assert len(r.issues) == 1
    assert r.issues[0].line_no == 2


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
