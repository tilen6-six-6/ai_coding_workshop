"""Load and validate a rule spec from YAML.

A spec is a list of rule definitions. Each rule has at minimum::

    - id: temperature_range
      check: range
      key: temperature
      severity: error
      params: {min: 0, max: 9000}

The ``check`` field selects one of the registered check types (see
``loginspect.rules.checks``). ``params`` are check-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from loginspect.model import Severity


@dataclass(slots=True)
class RuleSpec:
    id: str
    check: str
    severity: Severity
    key: str | None = None
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass(slots=True)
class SpecBundle:
    """A whole spec file: metadata plus a list of rules."""

    name: str
    version: str
    rules: list[RuleSpec] = field(default_factory=list)


def load_spec(path: str) -> SpecBundle:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("Spec file must be a mapping at the top level.")

    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("'rules' must be a list.")

    rules: list[RuleSpec] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_rules):
        if not isinstance(raw, dict):
            raise ValueError(f"Rule #{i} must be a mapping.")
        rid = raw.get("id")
        if not rid:
            raise ValueError(f"Rule #{i} is missing required field 'id'.")
        if rid in seen_ids:
            raise ValueError(f"Duplicate rule id: {rid!r}.")
        seen_ids.add(rid)
        check = raw.get("check")
        if not check:
            raise ValueError(f"Rule {rid!r} is missing required field 'check'.")
        rules.append(
            RuleSpec(
                id=rid,
                check=check,
                severity=Severity.from_name(raw.get("severity", "warning")),
                key=raw.get("key"),
                description=raw.get("description", ""),
                params=raw.get("params", {}) or {},
                enabled=raw.get("enabled", True),
            )
        )

    return SpecBundle(
        name=data.get("name", "unnamed-spec"),
        version=str(data.get("version", "0")),
        rules=rules,
    )
