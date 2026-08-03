"""Verification helper: an MCP client for the get_case_record tool exposed
by src/mock_services/transaction_history_server.py.

Unlike create_case_record.py and get_transaction_history.py, this has no
generated shim in src/tools/ -- get-case-record isn't declared anywhere in
the agent spec's tools[] list, since the agent itself never needs to read
a case record back. This file exists purely so verify_mcp_and_db.py can
prove create_case_record's write actually persisted, via a second,
independent MCP call.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MOCK_SERVER_PATH = _PROJECT_ROOT / "src" / "mock_services" / "transaction_history_server.py"

_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[str(_MOCK_SERVER_PATH)],
)


async def _call_async(**kwargs):
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_case_record", arguments=kwargs)
            return json.loads(result.content[0].text)


def call(**kwargs):
    return asyncio.run(_call_async(**kwargs))
