"""Generated capability handler for 'draft-case-narrative'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in
src/impl/handlers/draft_case_narrative.py, NOT here. That file
is scaffolded once and never overwritten by the generator.
"""

from __future__ import annotations

from src.impl.handlers import draft_case_narrative as _impl

CAPABILITY_ID = "draft-case-narrative"
INPUTS_SUMMARY = "{ alertId: string, transactions: array, riskProfile: object }"
OUTPUTS_SUMMARY = "{ alertId: string, narrative: string }"


def handle(input_data: dict) -> dict:
    """Draft a written case narrative from gathered evidence, in the format required for the case management system.

    Inputs : { alertId: string, transactions: array, riskProfile: object }
    Outputs: { alertId: string, narrative: string }
    """
    return _impl.handle(input_data)

