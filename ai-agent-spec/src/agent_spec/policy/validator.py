from __future__ import annotations

from dataclasses import dataclass, field

from agent_spec.parser.ast_nodes import AgentSpecAST
from agent_spec.policy.registry import PolicyError, all_rules

# Importing rules registers every @policy_rule-decorated function as a
# side effect of module load — this import exists for that effect.
from agent_spec.policy import rules as _rules  # noqa: F401


@dataclass
class PolicyReport:
    valid: bool
    errors: list[PolicyError] = field(default_factory=list)
    warnings: list[PolicyError] = field(default_factory=list)

    def print_summary(self) -> None:
        if self.valid:
            print("✅ Spec passes all policy rules.")
            return
        print(f"❌ Spec failed policy validation ({len(self.errors)} error(s)):\n")
        for err in self.errors:
            print(f"  - {err}")


def validate_policy(ast: AgentSpecAST) -> PolicyReport:
    """Run every registered policy rule against an already-parsed AST."""
    errors: list[PolicyError] = []
    for _rule_id, _description, rule_fn in all_rules():
        errors.extend(rule_fn(ast))
    return PolicyReport(valid=len(errors) == 0, errors=errors)
