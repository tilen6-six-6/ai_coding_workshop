"""LogInspect — a rules-driven log reviewer for embedded device telemetry.

Parses timestamped device-state snapshots and checks every field against a
declarative spec (enum membership, numeric min/max, required fields, fault
flags, state-sequence rules) to surface anything out of specification.
"""

__version__ = "0.1.0"

from loginspect.model import Finding, LogFile, Severity, Snapshot

__all__ = ["Snapshot", "LogFile", "Finding", "Severity", "__version__"]
