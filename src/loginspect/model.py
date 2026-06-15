"""Core data structures shared across the application."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class Severity(enum.IntEnum):
    """Ordered severity levels; higher is worse."""

    INFO = 10
    WARNING = 20
    ERROR = 30
    CRITICAL = 40

    @classmethod
    def from_name(cls, name: str) -> Severity:
        try:
            return cls[name.strip().upper()]
        except KeyError as exc:  # pragma: no cover - guarded by spec validation
            raise ValueError(f"Unknown severity: {name!r}") from exc


@dataclass(slots=True)
class Snapshot:
    """A single timestamped device-state record.

    ``fields`` maps a telemetry key (e.g. ``temperature``) to its raw string
    value as found in the log. Typed access is provided by helper methods so
    rules never have to repeat parsing logic.
    """

    index: int
    timestamp: datetime | None
    raw_timestamp: str
    fields: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)

    def as_int(self, key: str) -> int | None:
        value = self.fields.get(key)
        if value is None:
            return None
        try:
            return int(value, 0) if value.lower().startswith("0x") else int(value)
        except (ValueError, AttributeError):
            return None

    def as_float(self, key: str) -> float | None:
        value = self.fields.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


@dataclass(slots=True)
class LogFile:
    """A parsed log: an ordered collection of snapshots plus metadata."""

    path: str
    snapshots: list[Snapshot] = field(default_factory=list)
    source_format: str = "unknown"

    def __len__(self) -> int:
        return len(self.snapshots)

    @property
    def keys(self) -> set[str]:
        """All telemetry keys observed anywhere in the log."""
        seen: set[str] = set()
        for snap in self.snapshots:
            seen.update(snap.fields)
        return seen

    def series(self, key: str) -> list[tuple[int, str]]:
        """Return ``(snapshot_index, value)`` pairs where ``key`` is present."""
        return [(s.index, s.fields[key]) for s in self.snapshots if key in s.fields]


@dataclass(slots=True)
class Finding:
    """One detected deviation from spec."""

    rule_id: str
    severity: Severity
    key: str
    message: str
    snapshot_index: int | None = None
    raw_timestamp: str | None = None
    observed: Any = None
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.name,
            "key": self.key,
            "message": self.message,
            "snapshot_index": self.snapshot_index,
            "timestamp": self.raw_timestamp,
            "observed": self.observed,
            "expected": self.expected,
        }
