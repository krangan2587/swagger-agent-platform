"""Generated tool binding for 'escalate-to-investigator'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in src/impl/tools/escalate_to_investigator.py,
NOT here. That file is scaffolded once and never overwritten by the
generator -- this file just wires the declared contract (schema, auth
scopes, timeout, retry policy) to whatever you put there.
"""

from __future__ import annotations

from src.impl.tools import escalate_to_investigator as _impl

TOOL_ID = "escalate-to-investigator"
TOOL_TYPE = "http"
SIDE_EFFECTS = "irreversible"
TIMEOUT_MS = 10000
AUTH_SCOPES = ['case:escalate']


def call(**kwargs):
    """Escalate the case to a senior fraud investigator queue. This action cannot be automatically undone once the queue routes the case.

    type=http sideEffects=irreversible timeoutMs=10000
    """
    return _impl.call(**kwargs)

