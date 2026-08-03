"""
CLI: run Stage 4 (Template Engine + target adapter) and show the resulting
virtual file set.

Usage:
    generate-code path/to/agent.spec.yaml [--target python-service] [--out DIR]

Note: Stage 4's real contract (Section 7.4) produces a purely in-memory
virtual file set -- "Nothing is written to disk yet." Turning that into a
complete on-disk project (with docs, tests, deployment manifests, and a
changelog) is Stage 5's job -- the Output Packager -- which is a later
step in this build. When --out is given here, this command does a bare
write of just the templated files, as a convenience for inspecting what
Stage 4 produced. It is NOT the real Output Packager.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_spec.codegen import TemplateEngine, TemplateRenderError, get_target_adapter, list_target_adapters
from agent_spec.ir import build_ir
from agent_spec.parser import parse_spec_file
from agent_spec.pipeline import run_stage2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate-code",
        description="Run Stage 4 codegen (Template Engine + target adapter) for a validated spec.",
    )
    parser.add_argument("spec_file", type=Path)
    parser.add_argument(
        "--target",
        default="python-service",
        help=f"Target adapter id. Available: {', '.join(list_target_adapters())}",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Preview-write generated files under this directory (see module docstring)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Generate even if Stage 2 fails (debugging only)",
    )
    args = parser.parse_args(argv)

    if not args.spec_file.exists():
        print(f"❌ Spec file not found: {args.spec_file}", file=sys.stderr)
        return 2

    if not args.skip_validation:
        stage2 = run_stage2(args.spec_file)
        if not stage2.valid:
            print("❌ Cannot generate code: spec fails Stage 2 validation.\n", file=sys.stderr)
            stage2.print_summary()
            return 1

    try:
        adapter = get_target_adapter(args.target)
    except KeyError:
        print(
            f"❌ Unknown target adapter '{args.target}'. "
            f"Available: {', '.join(list_target_adapters())}",
            file=sys.stderr,
        )
        return 2

    ast = parse_spec_file(args.spec_file)
    ir = build_ir(ast)

    try:
        virtual_files = TemplateEngine(adapter).render(ir)
    except TemplateRenderError as e:
        print(f"❌ Template rendering failed: {e}", file=sys.stderr)
        return 1

    print(f"✅ Stage 4 produced {len(virtual_files)} file(s) for target '{args.target}':\n")
    for path in sorted(virtual_files):
        print(f"  {path}")

    if args.out:
        for rel_path, content in virtual_files.items():
            dest = args.out / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        print(f"\n📝 Preview-written to {args.out}/ (not the real Output Packager -- that's Step 6)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
