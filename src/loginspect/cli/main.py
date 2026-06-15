"""``loginspect`` command-line interface.

Examples::

    loginspect review log.txt --spec specs/gcu_p.yaml
    loginspect review log.txt --spec specs/gcu_p.yaml --format html -o report.html
    loginspect keys log.txt          # list telemetry keys observed
    loginspect formats               # list available parsers
"""

from __future__ import annotations

import argparse
import sys

from loginspect import __version__
from loginspect.model import Severity
from loginspect.parsers import available_formats, get_parser
from loginspect.parsers.base import autodetect
from loginspect.report import render_html, render_json, render_text, render_text_collapsed
from loginspect.rules import RuleEngine, load_spec


def _load_log(path: str, fmt: str | None):
    parser = get_parser(fmt) if fmt else autodetect(path)
    return parser.parse(path)


def _cmd_review(args: argparse.Namespace) -> int:
    log = _load_log(args.log, args.parser)
    spec = load_spec(args.spec)
    result = RuleEngine(spec).review(log)

    if args.format == "text":
        output = render_text_collapsed(result) if args.collapse else render_text(result)
    elif args.format == "json":
        output = render_json(result)
    else:
        output = render_html(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Wrote {args.format} report to {args.output}", file=sys.stderr)
    else:
        print(output)

    fail_at = Severity.from_name(args.fail_on)
    worst = max((f.severity for f in result.findings), default=Severity.INFO)
    if result.findings and worst >= fail_at:
        return 1
    return 0


def _cmd_keys(args: argparse.Namespace) -> int:
    log = _load_log(args.log, args.parser)
    for key in sorted(log.keys):
        print(key)
    print(f"\n{len(log.keys)} keys across {len(log)} snapshots", file=sys.stderr)
    return 0


def _cmd_formats(_: argparse.Namespace) -> int:
    for fmt in available_formats():
        print(fmt)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="loginspect", description=__doc__)
    ap.add_argument("--version", action="version", version=f"loginspect {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    rev = sub.add_parser("review", help="check a log against a spec")
    rev.add_argument("log", help="path to the log file")
    rev.add_argument("--spec", required=True, help="path to the rule spec (YAML)")
    rev.add_argument("--parser", choices=available_formats(),
                     help="force a parser instead of autodetecting")
    rev.add_argument("--format", choices=["text", "json", "html"], default="text")
    rev.add_argument("--collapse", action="store_true",
                     help="group repeated identical findings (text format)")
    rev.add_argument("-o", "--output", help="write report to a file instead of stdout")
    rev.add_argument("--fail-on", default="error",
                     choices=[s.name.lower() for s in Severity],
                     help="minimum severity that yields a non-zero exit code")
    rev.set_defaults(func=_cmd_review)

    keys = sub.add_parser("keys", help="list telemetry keys observed in a log")
    keys.add_argument("log")
    keys.add_argument("--parser", choices=available_formats())
    keys.set_defaults(func=_cmd_keys)

    fmts = sub.add_parser("formats", help="list available log parsers")
    fmts.set_defaults(func=_cmd_formats)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
