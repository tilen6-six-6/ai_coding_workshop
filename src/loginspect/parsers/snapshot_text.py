"""Parser for the ``[timestamp]`` + indented ``key: value`` snapshot format.

Example of one snapshot::

    [2026-06-11 15:25:55.003]
      main_sw: DW5060-GCU-P_MAIN_20260611_000_00_10.30.1
      gpio_value: 14680328
      temperature: 3698
      ...

Snapshots are separated by blank lines and/or the next timestamp header.
Line endings may be ``\\r\\n`` or ``\\n``.
"""

from __future__ import annotations

import re
from datetime import datetime

from loginspect.model import LogFile, Snapshot
from loginspect.parsers.base import BaseParser, register_parser

_TS_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s*$")
_KV_RE = re.compile(r"^\s+(?P<key>[A-Za-z0-9_]+):\s?(?P<val>.*?)\s*$")
_TS_FORMATS = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")


def _parse_ts(raw: str) -> datetime | None:
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


@register_parser
class SnapshotTextParser(BaseParser):
    name = "snapshot-text"

    def sniff(self, sample: str) -> bool:
        return bool(_TS_RE.match(sample.splitlines()[0])) if sample.strip() else False

    def parse(self, path: str) -> LogFile:
        log = LogFile(path=path, source_format=self.name)
        current: Snapshot | None = None
        index = 0
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\r\n")
                ts_match = _TS_RE.match(line)
                if ts_match:
                    if current is not None:
                        log.snapshots.append(current)
                    raw_ts = ts_match.group("ts")
                    current = Snapshot(
                        index=index,
                        timestamp=_parse_ts(raw_ts),
                        raw_timestamp=raw_ts,
                    )
                    index += 1
                    continue
                if current is None:
                    continue
                kv = _KV_RE.match(line)
                if kv:
                    current.fields[kv.group("key")] = kv.group("val")
        if current is not None:
            log.snapshots.append(current)
        return log
