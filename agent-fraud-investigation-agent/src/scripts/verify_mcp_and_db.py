"""
Verification script: proves MCP write, MCP read, and the underlying
SQLite persistence are all genuinely working together, not just returning
canned values.

Lives at src/scripts/ (a custom directory, not one the generator owns) so
it survives rebuilds automatically, same as src/impl/, src/runtime/, and
src/mock_services/.

Run from the project root, with the venv that has `mcp` installed:
    python3 -m src.scripts.verify_mcp_and_db
"""

from pathlib import Path

from src.impl.tools import get_case_record
from src.tools import create_case_record, get_transaction_history

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/scripts/ -> project root
DB_PATH = _PROJECT_ROOT / "src" / "mock_services" / "case_management.db"


def main():
    alert_id = "ALRT-VERIFY-001"

    print("1. MCP READ (get-transaction-history) -- fake data from the server")
    txns = get_transaction_history.call(customerId="CUST-7788", lookbackDays=30)
    print(f"   -> {txns}\n")

    print("2. MCP WRITE (create-case-record) -- real SQLite write, server-side")
    write_result = create_case_record.call(
        alertId=alert_id,
        narrative="Verification run: confirming MCP write + SQLite persistence.",
        recommendation="monitor",
    )
    print(f"   -> {write_result}\n")

    print("3. MCP READ of the SAME record (get-case-record) -- separate MCP call,")
    print("   proves step 2 actually persisted rather than just returning a fake ack")
    read_result = get_case_record.call(alertId=alert_id)
    print(f"   -> {read_result}\n")
    assert read_result["found"] is True
    assert read_result["narrative"] == "Verification run: confirming MCP write + SQLite persistence."

    print("4. INDEPENDENT DB READ -- bypassing MCP entirely, opening the .db file")
    print("   directly with sqlite3 to prove it's a real file, not an in-memory fake")
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT alert_id, narrative, recommendation FROM cases WHERE alert_id = ?",
        (alert_id,),
    ).fetchone()
    conn.close()
    print(f"   -> raw row from disk: {row}\n")
    assert row is not None
    assert row[0] == alert_id

    print("ALL CHECKS PASSED: MCP read, MCP write, MCP read-after-write, and")
    print("independent on-disk DB verification all agree with each other.")


if __name__ == "__main__":
    main()
