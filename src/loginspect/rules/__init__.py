"""Declarative rule engine. Rules are loaded from a spec file and evaluated
against a parsed log to produce findings.
"""

from loginspect.rules.checks import CHECK_TYPES
from loginspect.rules.engine import RuleEngine
from loginspect.rules.spec import RuleSpec, load_spec

__all__ = ["RuleSpec", "load_spec", "RuleEngine", "CHECK_TYPES"]
