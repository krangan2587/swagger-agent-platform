"""
CLI: dump a spec's parsed AST as JSON, so you can inspect what the Parser
built — including resolved $refs and source locations.

Usage:
    inspect-spec path/to/agent.spec.yaml
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from agent_spec.parser import ParserError, SourceLocation, parse_spec_file


def _json_default(obj):
    if isinstance(obj, SourceLocation):
        return str(obj)
    raise TypeError(f"not JSON serializable: {type(obj)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inspect-spec",
        description="Parse an AI Agent Specification file and print its AST as JSON.",
    )
    parser.add_argument("spec_file", type=Path)
    args = parser.parse_args(argv)

    try:
        ast = parse_spec_file(args.spec_file)
    except ParserError as e:
        print(f"❌ Parser error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    print(json.dumps(dataclasses.asdict(ast), indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
