"""Hand-written implementation for capability 'summarize-alert'.

This file is created once by the generator and NEVER overwritten by later
builds. The generated src/handlers/summarize_alert.py shim
always delegates to handle() below.
"""

from __future__ import annotations

from src.tools import get_transaction_history


def handle(input_data: dict) -> dict:
    # inputs : { alertId: string }
    # outputs: { alertId: string, summary: string, severity: string }
    alert_id = input_data["alertId"]

    # A real implementation would look up the alert's customerId from the
    # alerting system; hardcoded here since this capability's own inputs
    # schema doesn't carry it.
    txn_data = get_transaction_history.call(customerId="CUST-7788", lookbackDays=30)

    flagged = [t for t in txn_data["transactions"] if t.get("flagged")]
    severity = "high" if flagged else "low"
    summary = (
        f"Alert {alert_id}: {len(flagged)} flagged transaction(s) in the last "
        f"{txn_data['lookbackDays']} days, including {flagged[0]['merchant']}."
        if flagged
        else f"Alert {alert_id}: no flagged transactions found in the lookback window."
    )

    return {"alertId": alert_id, "summary": summary, "severity": severity}

