"""Generated tool binding for 'get-transaction-history'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in src/impl/tools/get_transaction_history.py,
NOT here. That file is scaffolded once and never overwritten by the
generator -- this file just wires the declared contract (schema, auth
scopes, timeout, retry policy) to whatever you put there.
"""

from __future__ import annotations

from src.impl.tools import get_transaction_history as _impl

TOOL_ID = "get-transaction-history"
TOOL_TYPE = "mcp"
SIDE_EFFECTS = "read"
TIMEOUT_MS = 8000
AUTH_SCOPES = ['fraud:read', 'txn:read']
RATE_LIMIT = {'maxCalls': 100, 'perSeconds': 60}
RETRY_POLICY = {'maxRetries': 3, 'backoff': 'exponential'}


def call(**kwargs):
    """Retrieve a customer's transaction history for a lookback window.

    type=mcp sideEffects=read timeoutMs=8000
    """
    return _impl.call(**kwargs)

