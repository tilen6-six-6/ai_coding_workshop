"""CLI for the log compliance checker.

Usage:
    python -m src.checker --rules rules/example_rules.yaml --logs logs/example.log
    python -m src.checker --rules r.yaml --logs a.log b.log --format json --out report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .parser import parse_file
from .rules_engine import evaluate, load_rules
from .models import LogEntry, Report

_SEV_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
_SEV_ICON = {"info": "·", "warning": "▲", "error": "✗", "critical": "‼"}


def _print_text(report: Report) -> None:
    if not report.issues:
        print(f"✓ PASS — {report.entries_checked} entries, "
              f"{report.rules_evaluated} rules, no issues.")
        return

    issues = sorted(report.issues,
                    key=lambda i: (-_SEV_ORDER.get(i.severity, 0), i.line_no or 0))
    print(f"{'PASS' if report.passed else 'FAIL'} — "
          f"{report.entries_checked} entries, {report.rules_evaluated} rules, "
          f"{len(report.issues)} issue(s)\n")
    for i in issues:
        icon = _SEV_ICON.get(i.severity, "?")
        loc = f"line {i.line_no}" if i.line_no else "whole-file"
        print(f"{icon} [{i.severity.upper()}] {i.rule_id} ({loc})")
        print(f"    {i.message}")
        if i.expected is not None or i.actual is not None:
            print(f"    expected: {i.expected!r}  actual: {i.actual!r}")
        if i.log_excerpt:
            print(f"    log: {i.log_excerpt}")
        print()


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check logs against compliance rules.")
    ap.add_argument("--rules", required=True, help="Path to rules YAML/JSON file.")
    ap.add_argument("--logs", required=True, nargs="+", help="One or more log files.")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--out", help="Write output to this file instead of stdout.")
    ap.add_argument("--fail-on", choices=["warning", "error", "critical", "never"],
                    default="error",
                    help="Minimum severity that makes the process exit non-zero.")
    args = ap.parse_args(argv)

    rules_doc = load_rules(args.rules)

    entries: List[LogEntry] = []
    offset = 0
    for path in args.logs:
        file_entries = parse_file(path)
        # keep line numbers unique-ish across files by tagging source
        for e in file_entries:
            e.fields.setdefault("_source", path)
        entries.extend(file_entries)
        offset += len(file_entries)

    report = evaluate(rules_doc, entries)

    if args.format == "json":
        output = json.dumps(report.to_dict(), indent=2, default=str)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Wrote JSON report to {args.out}")
        else:
            print(output)
    else:
        if args.out:
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                _print_text(report)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(buf.getvalue())
            print(f"Wrote text report to {args.out}")
        else:
            _print_text(report)

    # exit code
    if args.fail_on == "never":
        return 0
    threshold = _SEV_ORDER[args.fail_on]
    worst = max((_SEV_ORDER.get(i.severity, 0) for i in report.issues), default=-1)
    return 1 if worst >= threshold else 0


if __name__ == "__main__":
    sys.exit(main())
