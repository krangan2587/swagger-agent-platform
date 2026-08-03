"""Generated capability handler for 'recommend-disposition'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in
src/impl/handlers/recommend_disposition.py, NOT here. That file
is scaffolded once and never overwritten by the generator.
"""

from __future__ import annotations

from src.impl.handlers import recommend_disposition as _impl

CAPABILITY_ID = "recommend-disposition"
INPUTS_SUMMARY = "{ alertId: string, narrative: string }"
OUTPUTS_SUMMARY = "{ alertId: string, recommendation: string, confidence: number }"
SCOPE_BOUNDARIES = "A recommendation only. Escalation and account actions require a human analyst to invoke them explicitly."


def handle(input_data: dict) -> dict:
    """Recommend a disposition (e.g. escalate, monitor, close) for the case, with a confidence score and supporting rationale. Does not execute the disposition.

    Inputs : { alertId: string, narrative: string }
    Outputs: { alertId: string, recommendation: string, confidence: number }
    """
    return _impl.handle(input_data)

