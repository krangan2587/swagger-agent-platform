"""Hand-written implementation for tool 'create-case-record'.

This file is created once by the generator and NEVER overwritten by later
builds -- put your real mcp client code here. The generated
src/tools/create_case_record.py shim always delegates to call() below.

This is a genuine MCP client call (not a shortcut straight to SQLite):
the actual write happens server-side in
src/mock_services/transaction_history_server.py's create_case_record
tool, which persists to a real SQLite file on its own. This file's job is
only to speak the MCP protocol to get that write to happen.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/impl/tools/ -> project root
_MOCK_SERVER_PATH = _PROJECT_ROOT / "src" / "mock_services" / "transaction_history_server.py"

_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=[str(_MOCK_SERVER_PATH)],
)


async def _call_async(**kwargs):
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("create_case_record", arguments=kwargs)
            return json.loads(result.content[0].text)


def call(**kwargs):
    return asyncio.run(_call_async(**kwargs))
