"""Generated capability handler for 'gather-evidence'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in
src/impl/handlers/gather_evidence.py, NOT here. That file
is scaffolded once and never overwritten by the generator.
"""

from __future__ import annotations

from src.impl.handlers import gather_evidence as _impl

CAPABILITY_ID = "gather-evidence"
INPUTS_SUMMARY = "{ alertId: string, customerId: string }"
OUTPUTS_SUMMARY = "{ alertId: string, transactions: array, riskProfile: object }"


def handle(input_data: dict) -> dict:
    """Pull transaction history and the customer's current risk profile relevant to the flagged alert into a single evidence packet.

    Inputs : { alertId: string, customerId: string }
    Outputs: { alertId: string, transactions: array, riskProfile: object }
    """
    return _impl.handle(input_data)

