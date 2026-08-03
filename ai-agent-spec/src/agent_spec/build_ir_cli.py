"""
CLI: build the Stage 3 IR from a spec file. Per Section 7.3, the IR
Builder's contract is "input: the AST that passed Stage 2 validation" --
so this command runs the full Stage 2 gate first and refuses to build IR
for a spec that fails it, unless --skip-validation is passed for debugging.

Usage:
    build-ir path/to/agent.spec.yaml [-o agent.ir.json] [--stdout]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from agent_spec.ir import build_ir
from agent_spec.parser import parse_spec_file
from agent_spec.pipeline import run_stage2

_SPEC_SUFFIXES = (".spec.yaml", ".spec.yml", ".spec.json")


def _default_ir_path(spec_path: Path) -> Path:
    name = spec_path.name
    for suffix in _SPEC_SUFFIXES:
        if name.endswith(suffix):
            stem = name[: -len(suffix)]
            return spec_path.with_name(f"{stem}.ir.json")
    return spec_path.with_suffix(".ir.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build-ir",
        description="Build the target-agnostic IR (Stage 3) from a validated agent spec.",
    )
    parser.add_argument("spec_file", type=Path)
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="Where to write the IR JSON"
    )
    parser.add_argument(
        "--stdout", action="store_true", help="Print IR JSON to stdout instead of writing a file"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Build IR even if Stage 2 fails (debugging only -- not for the real pipeline)",
    )
    args = parser.parse_args(argv)

    if not args.spec_file.exists():
        print(f"❌ Spec file not found: {args.spec_file}", file=sys.stderr)
        return 2

    if not args.skip_validation:
        stage2 = run_stage2(args.spec_file)
        if not stage2.valid:
            print("❌ Cannot build IR: spec fails Stage 2 validation.\n", file=sys.stderr)
            stage2.print_summary()
            return 1

    ast = parse_spec_file(args.spec_file)
    ir = build_ir(ast)
    payload = json.dumps(dataclasses.asdict(ir), indent=2)

    if args.stdout:
        print(payload)
        return 0

    output_path = args.output or _default_ir_path(args.spec_file)
    output_path.write_text(payload, encoding="utf-8")
    print(f"✅ Wrote IR to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
