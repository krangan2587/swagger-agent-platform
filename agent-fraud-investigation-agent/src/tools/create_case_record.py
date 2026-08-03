"""Generated tool binding for 'create-case-record'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in src/impl/tools/create_case_record.py,
NOT here. That file is scaffolded once and never overwritten by the
generator -- this file just wires the declared contract (schema, auth
scopes, timeout, retry policy) to whatever you put there.
"""

from __future__ import annotations

from src.impl.tools import create_case_record as _impl

TOOL_ID = "create-case-record"
TOOL_TYPE = "mcp"
SIDE_EFFECTS = "write"
TIMEOUT_MS = 12000
AUTH_SCOPES = ['case:write']
RETRY_POLICY = {'maxRetries': 2, 'backoff': 'fixed'}


def call(**kwargs):
    """Create a new case record in the case management system.

    type=mcp sideEffects=write timeoutMs=12000
    """
    return _impl.call(**kwargs)

