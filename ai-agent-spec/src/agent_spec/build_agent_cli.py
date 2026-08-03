"""
CLI: run the full pipeline end to end -- Stage 2 gate, Stage 3 (IR),
Stage 4 (Template Engine), Stage 5 (Output Packager) -- producing a
complete, runnable agent project on disk.

Usage:
    build-agent path/to/agent.spec.yaml
    build-agent path/to/agent.spec.yaml --target python-service --out my-agent/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_spec.codegen import (
    TemplateEngine,
    TemplateRenderError,
    get_target_adapter,
    list_target_adapters,
)
from agent_spec.ir import build_ir
from agent_spec.packager import OutputPackager, OutputPackagerError
from agent_spec.parser import parse_spec_file
from agent_spec.pipeline import run_stage2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build-agent",
        description="Run the full 5-stage pipeline: spec -> validated, runnable agent project.",
    )
    parser.add_argument("spec_file", type=Path)
    parser.add_argument(
        "--target",
        default="python-service",
        help=f"Target adapter id. Available: {', '.join(list_target_adapters())}",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Output project directory (default: ./agent-<name>)"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(".agent-registry.json"),
        help="Local registry JSON used for CHANGELOG version history "
        "(default: ./.agent-registry.json)",
    )
    parser.add_argument(
        "--no-registry",
        action="store_true",
        help="Don't read or update a registry file -- CHANGELOG will show only this version",
    )
    parser.add_argument(
        "--skip-validation", action="store_true", help="Build even if Stage 2 fails (debugging only)"
    )
    args = parser.parse_args(argv)

    if not args.spec_file.exists():
        print(f"❌ Spec file not found: {args.spec_file}", file=sys.stderr)
        return 2

    if not args.skip_validation:
        stage2 = run_stage2(args.spec_file)
        if not stage2.valid:
            print("❌ Cannot build agent: spec fails Stage 2 validation.\n", file=sys.stderr)
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

    output_dir = args.out or Path(f"agent-{ir.info.name}")
    registry_path = None if args.no_registry else args.registry

    try:
        report = OutputPackager().build(
            virtual_files=virtual_files,
            ir=ir,
            spec_path=args.spec_file,
            output_dir=output_dir,
            registry_path=registry_path,
        )
    except OutputPackagerError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    changelog_state = "new" if report.changelog_entry_added else "unchanged"
    print(f"✅ Built agent project at {report.output_dir}/\n")
    print(f"  {len(report.files_written)} generated source file(s) under src/")
    print("  docs/reference.html")
    print(f"  spec/{args.spec_file.name}")
    print(f"  CHANGELOG.md ({changelog_state} entry for v{report.changelog_version})")
    print("  deploy/Dockerfile, deploy/manifest.yaml")
    print("  tests/unit/, tests/contract/, tests/eval/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
