"""Parse and normalize logs from several common formats into LogEntry objects.

Supported, auto-detected per line:
  - JSON object per line (JSONL):   {"level":"INFO","msg":"ok"}
  - key=value pairs:                level=INFO code=200 msg="ok"
  - syslog-ish:                     Jun 15 10:00:01 host app[123]: message
  - plain text fallback:            anything else -> {"message": <line>}

A whole-file JSON array is also supported (a top-level [ ... ]).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .models import LogEntry

# key=value or key="quoted value"
_KV_RE = re.compile(r'(\w[\w.\-]*)=("([^"]*)"|\'([^\']*)\'|\S+)')

# common timestamp keys to lift into LogEntry.timestamp
_TS_KEYS = ("timestamp", "time", "ts", "@timestamp", "datetime", "date")

# syslog: "Jun 15 10:00:01 host app[pid]: msg"
_SYSLOG_RE = re.compile(
    r'^(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+'
    r'(?P<app>[^\s:\[]+)(?:\[(?P<pid>\d+)\])?:\s*'
    r'(?P<msg>.*)$'
)

# ISO timestamp at start of line, e.g. 2026-06-15T10:00:01Z LEVEL msg
_ISO_PREFIX_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})?)\s+(?P<rest>.*)$'
)


def _lift_timestamp(fields: Dict[str, Any]) -> str | None:
    for k in _TS_KEYS:
        if k in fields and fields[k]:
            return str(fields[k])
    return None


def _coerce(value: str) -> Any:
    """Turn a string token into int/float/bool/None where it clearly is one."""
    v = value.strip()
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", "nil"):
        return None
    try:
        if re.fullmatch(r'-?\d+', v):
            return int(v)
        if re.fullmatch(r'-?\d*\.\d+', v):
            return float(v)
    except ValueError:
        pass
    return v


def _parse_kv(text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for m in _KV_RE.finditer(text):
        key = m.group(1)
        if m.group(3) is not None:
            out[key] = m.group(3)
        elif m.group(4) is not None:
            out[key] = m.group(4)
        else:
            out[key] = _coerce(m.group(2))
    return out


def parse_line(line_no: int, line: str) -> LogEntry:
    raw = line.rstrip("\n")
    stripped = raw.strip()
    if not stripped:
        return LogEntry(line_no=line_no, raw=raw, fields={})

    # 1) JSON object
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                return LogEntry(line_no=line_no, raw=raw, fields=obj,
                                timestamp=_lift_timestamp(obj))
        except json.JSONDecodeError:
            pass

    # 2) syslog
    m = _SYSLOG_RE.match(stripped)
    if m:
        fields: Dict[str, Any] = {
            "host": m.group("host"),
            "app": m.group("app"),
            "message": m.group("msg"),
        }
        if m.group("pid"):
            fields["pid"] = int(m.group("pid"))
        # also parse any kv pairs inside the message
        fields.update(_parse_kv(m.group("msg")))
        return LogEntry(line_no=line_no, raw=raw, fields=fields, timestamp=m.group("ts"))

    # 3) ISO-prefixed line
    m = _ISO_PREFIX_RE.match(stripped)
    rest = stripped
    ts = None
    if m:
        ts = m.group("ts")
        rest = m.group("rest")

    # 4) key=value pairs
    kv = _parse_kv(rest)
    if kv:
        return LogEntry(line_no=line_no, raw=raw, fields=kv,
                        timestamp=ts or _lift_timestamp(kv))

    # 5) plain text fallback
    return LogEntry(line_no=line_no, raw=raw, fields={"message": rest}, timestamp=ts)


def parse_text(text: str) -> List[LogEntry]:
    """Parse a whole file's text. Handles a top-level JSON array too."""
    s = text.strip()
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                entries = []
                for i, obj in enumerate(arr, start=1):
                    if isinstance(obj, dict):
                        entries.append(LogEntry(line_no=i, raw=json.dumps(obj),
                                                fields=obj, timestamp=_lift_timestamp(obj)))
                    else:
                        entries.append(LogEntry(line_no=i, raw=str(obj),
                                                fields={"message": obj}))
                return entries
        except json.JSONDecodeError:
            pass

    return [parse_line(i, line) for i, line in enumerate(text.splitlines(), start=1)
            if line.strip()]


def parse_file(path: str) -> List[LogEntry]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_text(f.read())
