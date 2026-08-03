"""
Stage 5 — Output Packager. Per Section 7.5:

Input:  the virtual file set from Stage 4, plus the AgentIR (for
        docs/changelog generation) and deployment.* fields
Output: a complete project directory on disk, ready for source control and CI
Failure mode: a missing expected file or an unwritable output path fails
        the run; partial output is not left in place -- the packager
        writes to a temporary directory and moves it into place atomically
        only on success.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import jinja2

from agent_spec.codegen.helpers import DEFAULT_HELPERS, snake_case
from agent_spec.ir.nodes import AgentIR
from agent_spec.packager.changelog import render_changelog
from agent_spec.packager.docs_renderer import render_reference_html
from agent_spec.packager.errors import OutputPackagerError
from agent_spec.packager.registry_store import (
    get_history,
    load_registry,
    record_version,
    save_registry,
)

_PACKAGING_TEMPLATES_DIR = Path(__file__).parent / "packaging_templates"


@dataclass
class PackagerReport:
    output_dir: Path
    files_written: list[str] = field(default_factory=list)
    changelog_entry_added: bool = False
    changelog_version: str | None = None


class OutputPackager:
    def __init__(self) -> None:
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_PACKAGING_TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,
        )
        for name, fn in DEFAULT_HELPERS.items():
            self._env.filters[name] = fn

    def build(
        self,
        virtual_files: dict[str, str],
        ir: AgentIR,
        spec_path: Path,
        output_dir: Path,
        registry_path: Path | None = None,
        changelog_date: date | None = None,
        changelog_notes: str | None = None,
    ) -> PackagerReport:
        changelog_date = changelog_date or date.today()

        # Step 1-5 all happen inside a temp staging dir; only on total
        # success do we touch the real output_dir at all (atomic move).
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "project"
            staging.mkdir()

            try:
                files_written = self._write_virtual_files(staging, virtual_files)  # step 1
                self._copy_spec(staging, spec_path)  # step 3
                self._write_docs(staging, ir)  # step 2
                changelog_added, changelog_version = self._write_changelog(
                    staging, ir, registry_path, changelog_date, changelog_notes
                )  # step 4
                self._write_deploy_manifests(staging, ir)  # step 5
                self._write_tests(staging, ir)  # generated tests, also Stage 5's job
                self._preserve_hand_written_impl(staging, output_dir, virtual_files)  # carry forward hand-written code
                self._scaffold_impl_stubs(staging, ir)  # fill in anything still missing
                self._ensure_package_init_files(staging)  # make src/ a real, importable tree
                self._consistency_check(staging, virtual_files)  # step 6
            except Exception as e:
                raise OutputPackagerError(f"packaging failed, no output written: {e}") from e

            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging), str(output_dir))

        return PackagerReport(
            output_dir=output_dir,
            files_written=files_written,
            changelog_entry_added=changelog_added,
            changelog_version=changelog_version,
        )

    # ---- individual steps --------------------------------------------------

    @staticmethod
    def _write_virtual_files(staging: Path, virtual_files: dict[str, str]) -> list[str]:
        written = []
        for rel_path, content in virtual_files.items():
            dest = staging / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written.append(rel_path)
        return written

    @staticmethod
    def _copy_spec(staging: Path, spec_path: Path) -> None:
        dest_dir = staging / "spec"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec_path, dest_dir / spec_path.name)

    @staticmethod
    def _write_docs(staging: Path, ir: AgentIR) -> None:
        dest_dir = staging / "docs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "reference.html").write_text(render_reference_html(ir), encoding="utf-8")

    @staticmethod
    def _write_changelog(
        staging: Path,
        ir: AgentIR,
        registry_path: Path | None,
        changelog_date: date,
        changelog_notes: str | None,
    ) -> tuple[bool, str]:
        agent_name = ir.info.name or "unknown-agent"
        version = ir.info.version or "0.0.0"

        registry_data = load_registry(registry_path) if registry_path else {}
        history = get_history(registry_data, agent_name)
        notes = changelog_notes or (
            "Initial recorded release." if not history else f"Generated from spec version {version}."
        )
        updated_data, added = record_version(
            registry_data, agent_name, version, changelog_date.isoformat(), notes
        )

        if registry_path:
            save_registry(registry_path, updated_data)

        final_history = get_history(updated_data, agent_name)
        (staging / "CHANGELOG.md").write_text(
            render_changelog(agent_name, final_history), encoding="utf-8"
        )
        return added, version

    def _write_deploy_manifests(self, staging: Path, ir: AgentIR) -> None:
        dest_dir = staging / "deploy"
        dest_dir.mkdir(parents=True, exist_ok=True)
        context = {"ir": ir}
        (dest_dir / "Dockerfile").write_text(
            self._env.get_template("Dockerfile.j2").render(**context), encoding="utf-8"
        )
        (dest_dir / "manifest.yaml").write_text(
            self._env.get_template("manifest.yaml.j2").render(**context), encoding="utf-8"
        )

    def _write_tests(self, staging: Path, ir: AgentIR) -> None:
        unit_dir = staging / "tests" / "unit"
        contract_dir = staging / "tests" / "contract"
        eval_dir = staging / "tests" / "eval"
        for d in (unit_dir, contract_dir, eval_dir):
            d.mkdir(parents=True, exist_ok=True)

        unit_tpl = self._env.get_template("unit_test.py.j2")
        contract_tpl = self._env.get_template("contract_test.py.j2")
        for tool in ir.tools:
            base = f"test_{snake_case(tool.id)}"
            (unit_dir / f"{base}.py").write_text(
                unit_tpl.render(ir=ir, tool=tool), encoding="utf-8"
            )
            (contract_dir / f"{base}_contract.py").write_text(
                contract_tpl.render(ir=ir, tool=tool), encoding="utf-8"
            )

        eval_tpl = self._env.get_template("eval_test.py.j2")
        (eval_dir / "test_eval_suite.py").write_text(eval_tpl.render(ir=ir), encoding="utf-8")

    @staticmethod
    def _preserve_hand_written_impl(
        staging: Path, output_dir: Path, virtual_files: dict[str, str]
    ) -> None:
        """Carry forward hand-written code from a previous build. Any
        top-level directory under src/ that Stage 4's manifest did NOT
        produce output into this run (src/impl/, src/runtime/, or any
        other custom directory a developer adds) is treated as belonging
        to the developer, not the generator -- so a rebuild must not
        destroy it. Directories the manifest DOES own (src/tools/,
        src/handlers/, src/guardrails/, src/prompts/, src/memory/, ...)
        are regenerated fresh every time, as designed."""
        previous_src = output_dir / "src"
        if not previous_src.exists():
            return

        generator_owned_dirs = {
            Path(rel_path).parts[1]
            for rel_path in virtual_files
            if Path(rel_path).parts[0] == "src" and len(Path(rel_path).parts) > 1
        }

        for child in previous_src.iterdir():
            if not child.is_dir() or child.name in generator_owned_dirs:
                continue
            dest = staging / "src" / child.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(child, dest)

    @staticmethod
    def _scaffold_impl_stubs(staging: Path, ir: AgentIR) -> None:
        """Create src/impl/tools/<id>.py and src/impl/handlers/<id>.py the
        FIRST time each is needed, and never again -- if
        _preserve_hand_written_impl already recovered a file from a prior
        build, it's left completely alone."""
        tools_dir = staging / "src" / "impl" / "tools"
        handlers_dir = staging / "src" / "impl" / "handlers"
        tools_dir.mkdir(parents=True, exist_ok=True)
        handlers_dir.mkdir(parents=True, exist_ok=True)
        (staging / "src" / "impl" / "__init__.py").touch(exist_ok=True)
        (tools_dir / "__init__.py").touch(exist_ok=True)
        (handlers_dir / "__init__.py").touch(exist_ok=True)

        for tool in ir.tools:
            path = tools_dir / f"{snake_case(tool.id)}.py"
            if path.exists():
                continue  # preserved from a previous build -- do not touch
            path.write_text(
                f'''"""Hand-written implementation for tool '{tool.id}'.

This file is created once by the generator and NEVER overwritten by later
builds -- put your real {tool.type} client code here. The generated
src/tools/{snake_case(tool.id)}.py shim always delegates to call() below.
"""

from __future__ import annotations


def call(**kwargs):
    # TODO: implement the real {tool.type} call for '{tool.id}'.
    raise NotImplementedError("tool '{tool.id}' has no real implementation yet")
''',
                encoding="utf-8",
            )

        for capability in ir.capabilities:
            path = handlers_dir / f"{snake_case(capability.id)}.py"
            if path.exists():
                continue  # preserved from a previous build -- do not touch
            path.write_text(
                f'''"""Hand-written implementation for capability '{capability.id}'.

This file is created once by the generator and NEVER overwritten by later
builds. The generated src/handlers/{snake_case(capability.id)}.py shim
always delegates to handle() below.
"""

from __future__ import annotations


def handle(input_data: dict) -> dict:
    # TODO: implement capability '{capability.id}'.
    # inputs : {capability.inputs_summary}
    # outputs: {capability.outputs_summary}
    raise NotImplementedError("capability '{capability.id}' has no real implementation yet")
''',
                encoding="utf-8",
            )

    @staticmethod
    def _ensure_package_init_files(staging: Path) -> None:
        """Make every directory under src/ (including src/ itself) an
        importable Python package -- guaranteed on every rebuild -- so the
        generated shims' `from src.impl.tools import ...` imports work
        regardless of how the project is run."""
        src_dir = staging / "src"
        if not src_dir.exists():
            return
        for d in [src_dir, *(p for p in src_dir.rglob("*") if p.is_dir())]:
            init_file = d / "__init__.py"
            if not init_file.exists():
                init_file.touch()

    @staticmethod
    def _consistency_check(staging: Path, virtual_files: dict[str, str]) -> None:
        """Step 6: 'confirm every file the manifest expected was actually
        produced, and that no template error from Stage 4 was silently
        dropped.'"""
        for rel_path, expected_content in virtual_files.items():
            dest = staging / rel_path
            if not dest.exists():
                raise OutputPackagerError(f"expected file missing after write: {rel_path}")
            if dest.read_text(encoding="utf-8") != expected_content:
                raise OutputPackagerError(f"file content mismatch after write: {rel_path}")
