"""Generated capability handler for 'summarize-alert'.

DO NOT EDIT BY HAND -- generated from the agent spec by the Template Engine
(Stage 4, target: python-service). Re-run the generator instead.

Your real implementation goes in
src/impl/handlers/summarize_alert.py, NOT here. That file
is scaffolded once and never overwritten by the generator.
"""

from __future__ import annotations

from src.impl.handlers import summarize_alert as _impl

CAPABILITY_ID = "summarize-alert"
INPUTS_SUMMARY = "{ alertId: string }"
OUTPUTS_SUMMARY = "{ alertId: string, summary: string, severity: string }"
SCOPE_BOUNDARIES = "Summarization only -- does not determine disposition."


def handle(input_data: dict) -> dict:
    """Summarize a fraud-detection alert in plain language for the assigned analyst, including why it fired and its severity.

    Inputs : { alertId: string }
    Outputs: { alertId: string, summary: string, severity: string }
    """
    return _impl.handle(input_data)

