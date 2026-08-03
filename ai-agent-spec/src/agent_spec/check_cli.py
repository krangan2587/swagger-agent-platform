"""
CLI: run the full Stage 2 gate (schema validation + policy validation).

Usage:
    check-spec path/to/agent.spec.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_spec.pipeline import run_stage2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-spec",
        description="Run schema + policy validation (Stage 2) on an agent spec.",
    )
    parser.add_argument("spec_file", type=Path)
    args = parser.parse_args(argv)

    if not args.spec_file.exists():
        print(f"❌ Spec file not found: {args.spec_file}", file=sys.stderr)
        return 2

    report = run_stage2(args.spec_file)
    report.print_summary()
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
