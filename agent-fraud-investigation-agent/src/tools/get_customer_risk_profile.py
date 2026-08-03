"""Generated tool binding for 'get-customer-risk-profile'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in src/impl/tools/get_customer_risk_profile.py,
NOT here. That file is scaffolded once and never overwritten by the
generator -- this file just wires the declared contract (schema, auth
scopes, timeout, retry policy) to whatever you put there.
"""

from __future__ import annotations

from src.impl.tools import get_customer_risk_profile as _impl

TOOL_ID = "get-customer-risk-profile"
TOOL_TYPE = "http"
SIDE_EFFECTS = "read"
TIMEOUT_MS = 5000
AUTH_SCOPES = ['risk:read']
RATE_LIMIT = {'maxCalls': 120, 'perSeconds': 60}


def call(**kwargs):
    """Retrieve the customer's current composite risk score and signals.

    type=http sideEffects=read timeoutMs=5000
    """
    return _impl.call(**kwargs)

