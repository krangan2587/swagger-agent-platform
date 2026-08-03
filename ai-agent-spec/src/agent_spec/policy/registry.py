"""
Stage 2b — Policy Validator. Per Section 7.2b of the reference doc:

"Policy rules are implemented as small, independently testable predicate
functions registered against the AST — each rule is a pure function of
(ast) -> error[] — rather than embedded in the schema or hand-coded inline
in the Validator."

This module is just the registry + the @policy_rule decorator. The actual
rules live in rules.py, each one registering itself on import.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent_spec.parser.ast_nodes import AgentSpecAST
from agent_spec.parser.location import SourceLocation


@dataclass
class PolicyError:
    rule_id: str
    message: str
    location: SourceLocation | None = None

    def __str__(self) -> str:
        loc = f"{self.location}: " if self.location else ""
        return f"{loc}[{self.rule_id}] {self.message}"


RuleFn = Callable[[AgentSpecAST], list[PolicyError]]

# (rule_id, human-readable description, the predicate function itself)
_REGISTRY: list[tuple[str, str, RuleFn]] = []


def policy_rule(rule_id: str, description: str):
    """Decorator that registers a rule function under a stable id.

    The rule set is versioned separately from the schema (Section 7.2's
    design note) — a new compliance requirement is just a new function
    decorated with @policy_rule; it needs no specVersion bump.
    """

    def decorator(fn: RuleFn) -> RuleFn:
        _REGISTRY.append((rule_id, description, fn))
        return fn

    return decorator


def all_rules() -> list[tuple[str, str, RuleFn]]:
    return list(_REGISTRY)
