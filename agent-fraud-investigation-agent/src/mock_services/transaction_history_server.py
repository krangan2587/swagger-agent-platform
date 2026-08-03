"""A tiny, real MCP server standing in for the bank's transaction-history
and case-management services.

Lives at src/mock_services/ (a custom directory, not one the generator
owns) so it survives rebuilds -- same protection as src/impl/ and
src/runtime/: anything under src/ that isn't tools/, handlers/,
guardrails/, prompts/, or memory/ is treated as yours and preserved.

It represents entirely separate, independently-deployed systems -- in
production these would be someone else's services, running somewhere
else, that this agent merely connects to as an MCP client. It's launched
as a subprocess by the tool bindings in src/impl/tools/, communicating
over real stdio, exactly like a real MCP server would.

Two tools are exposed:
  - get_transaction_history: read-only, fake in-memory data (no real
    persistence -- a real implementation would query the core banking
    system).
  - create_case_record / get_case_record: a genuine SQLite-backed write
    and read, so a case record created via one MCP call can be read back
    via another, entirely server-side.
"""

import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fraud-services")

_DB_PATH = Path(__file__).parent / "case_management.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            alert_id TEXT PRIMARY KEY,
            narrative TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


@mcp.tool()
def get_transaction_history(customerId: str, lookbackDays: int) -> dict:
    """Return a customer's transaction history for the given lookback window."""
    # Stand-in "database" -- a real implementation would query the core
    # banking system. Deliberately NOT persisted -- this tool is read-only
    # in the spec (sideEffects: read) and has nothing to write.
    fake_transactions = [
        {"id": "TXN-1", "amount": 4500.00, "merchant": "Wire Transfer - Overseas", "flagged": True},
        {"id": "TXN-2", "amount": 12.50, "merchant": "Coffee Shop", "flagged": False},
    ]
    return {
        "customerId": customerId,
        "lookbackDays": lookbackDays,
        "transactions": fake_transactions,
    }


@mcp.tool()
def create_case_record(alertId: str, narrative: str, recommendation: str) -> dict:
    """Create (or replace) a case record. A genuine write, persisted to a
    real SQLite database on the server side -- not just in memory."""
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cases (alert_id, narrative, recommendation) "
            "VALUES (?, ?, ?)",
            (alertId, narrative, recommendation),
        )
        conn.commit()
    finally:
        conn.close()
    return {"caseId": f"CASE-{alertId}", "status": "created"}


@mcp.tool()
def get_case_record(alertId: str) -> dict:
    """Read back a previously created case record. Proves create_case_record's
    write actually persisted -- this is a separate MCP call, reading from
    the same on-disk SQLite file, not anything cached in memory."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT alert_id, narrative, recommendation, created_at FROM cases WHERE alert_id = ?",
            (alertId,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return {"found": False, "alertId": alertId}

    return {
        "found": True,
        "alertId": row[0],
        "narrative": row[1],
        "recommendation": row[2],
        "createdAt": row[3],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
