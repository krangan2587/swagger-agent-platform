"""
The five representative policy rules from Section 7.2b of the reference doc.

Each function is a pure predicate: (AgentSpecAST) -> list[PolicyError].
Import this module for its side effect of registering every rule with
the @policy_rule decorator — that's why `policy/__init__.py` imports it
even though nothing here is called directly by name.
"""

from __future__ import annotations

import re

from agent_spec.parser.ast_nodes import AgentSpecAST
from agent_spec.policy.registry import PolicyError, policy_rule

# The centrally maintained approved-provider list (Section 7.2b, rule 3).
# In a real system this would be looked up from a registry/config service,
# not hardcoded — this constant is a placeholder for that lookup.
APPROVED_MODEL_PROVIDERS = frozenset({"internal-model-gateway"})

_CREDENTIALS_REF_PATTERN = re.compile(r"^secretsmanager://")

_WRITE_LIKE_SIDE_EFFECTS = frozenset({"write", "irreversible"})
_WRITE_LIKE_DATA_OPS = frozenset({"write", "delete"})


@policy_rule(
    "require-checkpoints-for-write-effects",
    "A tool with write/irreversible side effects, or a dataContract "
    "allowing write/delete, requires humanInLoop.checkpoints to be non-empty.",
)
def _require_checkpoints_for_write_effects(ast: AgentSpecAST) -> list[PolicyError]:
    checkpoints = ast.human_in_loop.checkpoints if ast.human_in_loop else []
    if checkpoints:
        return []

    errors: list[PolicyError] = []
    for tool in ast.tools:
        if tool.side_effects in _WRITE_LIKE_SIDE_EFFECTS:
            errors.append(
                PolicyError(
                    "require-checkpoints-for-write-effects",
                    f"tool '{tool.id}' has sideEffects={tool.side_effects!r} "
                    "but humanInLoop.checkpoints is empty or absent",
                    tool.source_location,
                )
            )
    for dc in ast.data_contracts:
        risky_ops = [op for op in dc.allowed_operations if op in _WRITE_LIKE_DATA_OPS]
        if risky_ops:
            errors.append(
                PolicyError(
                    "require-checkpoints-for-write-effects",
                    f"dataContract '{dc.source}' allows {risky_ops} "
                    "but humanInLoop.checkpoints is empty or absent",
                    dc.source_location,
                )
            )
    return errors


@policy_rule(
    "require-pii-handling-for-pii-data",
    "A dataContract with piiPresent=true requires guardrails.piiHandling to be set.",
)
def _require_pii_handling_for_pii_data(ast: AgentSpecAST) -> list[PolicyError]:
    if ast.guardrails and ast.guardrails.pii_handling:
        return []

    return [
        PolicyError(
            "require-pii-handling-for-pii-data",
            f"dataContract '{dc.source}' has piiPresent=true but "
            "guardrails.piiHandling is not set",
            dc.source_location,
        )
        for dc in ast.data_contracts
        if dc.pii_present
    ]


@policy_rule(
    "restricted-data-requires-approved-provider",
    "A dataContract with classification=restricted requires model.provider "
    "to be on the approved-provider list.",
)
def _restricted_data_requires_approved_provider(ast: AgentSpecAST) -> list[PolicyError]:
    if not any(dc.classification == "restricted" for dc in ast.data_contracts):
        return []

    provider = ast.model.provider if ast.model else None
    if provider in APPROVED_MODEL_PROVIDERS:
        return []

    return [
        PolicyError(
            "restricted-data-requires-approved-provider",
            f"a dataContract has classification='restricted' but "
            f"model.provider={provider!r} is not on the approved list "
            f"({sorted(APPROVED_MODEL_PROVIDERS)})",
            ast.model.source_location if ast.model else None,
        )
    ]


@policy_rule(
    "credentials-ref-must-be-secret-manager-reference",
    "auth.credentialsRef must reference a secret manager, never a literal secret.",
)
def _credentials_ref_must_be_secret_manager_reference(ast: AgentSpecAST) -> list[PolicyError]:
    cred = ast.auth.credentials_ref if ast.auth else None
    if not cred or _CREDENTIALS_REF_PATTERN.match(cred):
        return []

    return [
        PolicyError(
            "credentials-ref-must-be-secret-manager-reference",
            f"auth.credentialsRef={cred!r} does not match the required "
            "'^secretsmanager://' pattern — literal secrets are rejected outright",
            ast.auth.source_location,
        )
    ]


@policy_rule(
    "production-requires-deployment-approval",
    "info.lifecycle=production requires deployment.approvalRequired=true.",
)
def _production_requires_deployment_approval(ast: AgentSpecAST) -> list[PolicyError]:
    if not ast.info or ast.info.lifecycle != "production":
        return []
    if ast.deployment and ast.deployment.approval_required is True:
        return []

    loc = ast.deployment.source_location if ast.deployment else ast.info.source_location
    return [
        PolicyError(
            "production-requires-deployment-approval",
            "info.lifecycle='production' requires deployment.approvalRequired=true",
            loc,
        )
    ]
