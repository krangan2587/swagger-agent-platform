"""
CLI for the AI Agent Specification tooling.

Usage:
    validate-spec path/to/agent.spec.yaml
    python -m agent_spec.cli path/to/agent.spec.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_spec.validator import validate_spec_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate-spec",
        description="Validate an AI Agent Specification file against the schema.",
    )
    parser.add_argument("spec_file", type=Path, help="Path to a .yaml/.yml/.json spec file")
    args = parser.parse_args(argv)

    try:
        report = validate_spec_file(args.spec_file)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2
    except Exception as e:  # malformed YAML/JSON, etc.
        print(f"❌ Could not parse spec file: {e}", file=sys.stderr)
        return 2

    report.print_summary()
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
