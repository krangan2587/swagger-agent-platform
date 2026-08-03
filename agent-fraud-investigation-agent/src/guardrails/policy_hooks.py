"""Generated guardrail enforcement hooks.

DO NOT EDIT BY HAND -- generated from the agent spec's guardrails section by
the Template Engine (Stage 4, target: python-service).
"""

from __future__ import annotations

CONTENT_POLICIES = ['no-account-freeze-without-approval', 'no-customer-contact', 'confidentiality-required']
BUSINESS_RULES = ['escalation_requires_severity_high_or_critical', 'dual_control_over_10000_usd', 'narrative_must_cite_evidence_source']
REFUSAL_CONDITIONS = ['request_to_execute_account_action', 'request_outside_fraud_scope', 'request_for_unmasked_pii']
MAX_AUTONOMY_STEPS = 8
PII_HANDLING = "mask"

# Derived in the IR Builder (Stage 3) from write/irreversible tools and/or
# an autonomy-step ceiling -- see AgentIR.requires_human_approval.
REQUIRES_HUMAN_APPROVAL = True


def check_refusal(request: dict) -> str | None:
    """Return a refusal reason if `request` matches a refusal condition,
    otherwise None. TODO: wire each entry in REFUSAL_CONDITIONS to real
    detection logic."""
    return None


def enforce_pii_handling(payload: dict) -> dict:
    """Apply PII_HANDLING to `payload` before it leaves the agent.
    TODO: implement based on PII_HANDLING's value."""
    return payload
