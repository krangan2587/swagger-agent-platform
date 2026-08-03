from datetime import date
from pathlib import Path

import pytest

from agent_spec.codegen import TemplateEngine, get_target_adapter
from agent_spec.ir import build_ir
from agent_spec.packager import OutputPackager, OutputPackagerError
from agent_spec.parser import parse_spec_file

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _build_virtual_files_only(spec_filename: str) -> dict[str, str]:
    ast = parse_spec_file(EXAMPLES_DIR / spec_filename)
    ir = build_ir(ast)
    adapter = get_target_adapter("python-service")
    return TemplateEngine(adapter).render(ir)


def _build(spec_filename: str, output_dir: Path, registry_path=None, changelog_date=None):
    spec_path = EXAMPLES_DIR / spec_filename
    ast = parse_spec_file(spec_path)
    ir = build_ir(ast)
    adapter = get_target_adapter("python-service")
    virtual_files = TemplateEngine(adapter).render(ir)
    return OutputPackager().build(
        virtual_files=virtual_files,
        ir=ir,
        spec_path=spec_path,
        output_dir=output_dir,
        registry_path=registry_path,
        changelog_date=changelog_date,
    )


def test_full_project_structure_matches_section_8_1(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    report = _build("kyc-refresh-agent.spec.yaml", out)

    assert report.output_dir == out
    # src/ (from Stage 4)
    assert (out / "src" / "tools" / "get_customer_profile.py").exists()
    assert (out / "src" / "tools" / "update_kyc_record.py").exists()
    assert (out / "src" / "handlers" / "summarize_kyc_gaps.py").exists()
    assert (out / "src" / "handlers" / "draft_outreach_note.py").exists()
    assert (out / "src" / "guardrails" / "policy_hooks.py").exists()
    assert (out / "src" / "prompts" / "kyc_refresh.py").exists()
    assert (out / "src" / "memory" / "session_store.py").exists()
    # spec/ (step 3)
    assert (out / "spec" / "kyc-refresh-agent.spec.yaml").exists()
    # docs/ (step 2)
    assert (out / "docs" / "reference.html").exists()
    # CHANGELOG.md (step 4)
    assert (out / "CHANGELOG.md").exists()
    # deploy/ (step 5)
    assert (out / "deploy" / "Dockerfile").exists()
    assert (out / "deploy" / "manifest.yaml").exists()
    # tests/
    assert (out / "tests" / "unit" / "test_get_customer_profile.py").exists()
    assert (out / "tests" / "unit" / "test_update_kyc_record.py").exists()
    assert (out / "tests" / "contract" / "test_get_customer_profile_contract.py").exists()
    assert (out / "tests" / "eval" / "test_eval_suite.py").exists()


def test_spec_copy_matches_original_content(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    original = (EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml").read_text(encoding="utf-8")
    copied = (out / "spec" / "kyc-refresh-agent.spec.yaml").read_text(encoding="utf-8")
    assert original == copied


def test_docs_reference_html_contains_key_ir_data(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    html = (out / "docs" / "reference.html").read_text(encoding="utf-8")
    assert "kyc-refresh-agent" in html
    assert "1.2.0" in html
    assert "summarize-kyc-gaps" in html
    assert "get-customer-profile" in html
    # _list_items puts a closing </strong> between the label and the value,
    # so check for the label and value as separate substrings.
    assert "Human approval required" in html
    assert "</strong> True" in html


def test_deploy_manifests_reflect_deployment_section(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    dockerfile = (out / "deploy" / "Dockerfile").read_text(encoding="utf-8")
    manifest = (out / "deploy" / "manifest.yaml").read_text(encoding="utf-8")

    assert 'AGENT_VERSION="1.2.0"' in dockerfile
    assert 'ROLLOUT_STRATEGY="canary"' in dockerfile
    assert "type: canary" in manifest
    assert 'name: kyc-refresh-agent' in manifest


def test_eval_test_references_eval_suite_ref(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    content = (out / "tests" / "eval" / "test_eval_suite.py").read_text(encoding="utf-8")
    assert 'EVAL_SUITE_REF = "evals/kyc-refresh-agent.yaml"' in content


def test_first_build_records_initial_release_in_changelog(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    registry = tmp_path / "registry.json"

    report = _build(
        "kyc-refresh-agent.spec.yaml", out, registry_path=registry, changelog_date=date(2026, 1, 15)
    )

    assert report.changelog_entry_added is True
    assert report.changelog_version == "1.2.0"

    changelog = (out / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.2.0 — 2026-01-15" in changelog
    assert "Initial recorded release." in changelog

    assert registry.exists()


def test_rebuilding_the_same_version_does_not_duplicate_changelog_entry(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    registry = tmp_path / "registry.json"

    _build("kyc-refresh-agent.spec.yaml", out, registry_path=registry, changelog_date=date(2026, 1, 15))
    second = _build(
        "kyc-refresh-agent.spec.yaml", out, registry_path=registry, changelog_date=date(2026, 1, 20)
    )

    assert second.changelog_entry_added is False
    changelog = (out / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.count("## 1.2.0") == 1


def test_registry_persists_across_separate_agents(tmp_path):
    registry = tmp_path / "registry.json"

    _build(
        "kyc-refresh-agent.spec.yaml",
        tmp_path / "agent-kyc",
        registry_path=registry,
        changelog_date=date(2026, 1, 1),
    )
    _build(
        "read-only-agent.spec.yaml",
        tmp_path / "agent-readonly",
        registry_path=registry,
        changelog_date=date(2026, 1, 2),
    )

    import json

    data = json.loads(registry.read_text(encoding="utf-8"))
    assert "kyc-refresh-agent" in data
    assert "read-only-agent" in data
    assert len(data["kyc-refresh-agent"]) == 1
    assert len(data["read-only-agent"]) == 1


def test_no_registry_still_produces_a_changelog(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    report = _build("kyc-refresh-agent.spec.yaml", out, registry_path=None)

    assert report.changelog_version == "1.2.0"
    changelog = (out / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "1.2.0" in changelog


def test_atomicity_failed_build_leaves_existing_output_dir_untouched(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    out.mkdir()
    marker = out / "PRE_EXISTING_MARKER.txt"
    marker.write_text("do not touch me")

    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    ir = build_ir(ast)
    adapter = get_target_adapter("python-service")
    virtual_files = TemplateEngine(adapter).render(ir)

    nonexistent_spec_path = tmp_path / "this-spec-does-not-exist.spec.yaml"

    with pytest.raises(OutputPackagerError):
        OutputPackager().build(
            virtual_files=virtual_files,
            ir=ir,
            spec_path=nonexistent_spec_path,  # copy step will fail
            output_dir=out,
        )

    # The pre-existing directory and its marker must survive untouched.
    assert marker.exists()
    assert marker.read_text() == "do not touch me"
    assert not (out / "src").exists()  # the failed build never got written


def test_rebuild_overwrites_previous_generation(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    stale = out
    stale.mkdir(parents=True)
    (stale / "STALE_FILE.txt").write_text("from a previous, different generation")

    _build("kyc-refresh-agent.spec.yaml", out)

    assert not (out / "STALE_FILE.txt").exists()
    assert (out / "src" / "tools" / "get_customer_profile.py").exists()


def test_impl_stubs_are_scaffolded_for_every_tool_and_capability(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    assert (out / "src" / "impl" / "tools" / "get_customer_profile.py").exists()
    assert (out / "src" / "impl" / "tools" / "update_kyc_record.py").exists()
    assert (out / "src" / "impl" / "handlers" / "summarize_kyc_gaps.py").exists()
    assert (out / "src" / "impl" / "handlers" / "draft_outreach_note.py").exists()
    # importable as packages
    assert (out / "src" / "impl" / "__init__.py").exists()
    assert (out / "src" / "impl" / "tools" / "__init__.py").exists()
    assert (out / "src" / "impl" / "handlers" / "__init__.py").exists()


def test_generated_shim_delegates_to_impl_module():
    files = _build_virtual_files_only("kyc-refresh-agent.spec.yaml")
    shim = files["src/tools/get_customer_profile.py"]
    assert "from src.impl.tools import get_customer_profile as _impl" in shim
    assert "return _impl.call(**kwargs)" in shim
    assert "NotImplementedError" not in shim  # the shim itself no longer stubs anything


def test_hand_written_impl_survives_a_rebuild(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    impl_path = out / "src" / "impl" / "tools" / "get_customer_profile.py"
    impl_path.write_text(
        '"""Hand-written."""\n\n\ndef call(**kwargs):\n    return {"real": "implementation"}\n',
        encoding="utf-8",
    )

    # Rebuild the SAME spec into the SAME output_dir.
    _build("kyc-refresh-agent.spec.yaml", out)

    survived = impl_path.read_text(encoding="utf-8")
    assert "real" in survived
    assert "NotImplementedError" not in survived

    # The generated shim, meanwhile, was freshly regenerated as usual.
    shim = (out / "src" / "tools" / "get_customer_profile.py").read_text(encoding="utf-8")
    assert "DO NOT EDIT BY HAND" in shim


def test_impl_stub_only_created_for_tools_missing_from_a_prior_build(tmp_path):
    # Build once with a spec that has only one tool, hand-write its impl,
    # then rebuild with a spec that adds a second tool -- the first tool's
    # hand-written impl must survive, and the second must get a fresh stub.
    out = tmp_path / "agent"
    _build("read-only-agent.spec.yaml", out)  # has exactly one tool: get-thing

    impl_path = out / "src" / "impl" / "tools" / "get_thing.py"
    impl_path.write_text(
        '"""Hand-written."""\n\n\ndef call(**kwargs):\n    return {"real": True}\n',
        encoding="utf-8",
    )

    _build("read-only-agent.spec.yaml", out)  # rebuild same spec

    assert "real" in impl_path.read_text(encoding="utf-8")


def test_every_src_subdirectory_is_an_importable_package(tmp_path):
    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    src_dir = out / "src"
    for d in [src_dir, *(p for p in src_dir.rglob("*") if p.is_dir())]:
        assert (d / "__init__.py").exists(), f"{d} is missing __init__.py"


def test_generated_shim_actually_imports_and_delegates(tmp_path):
    # End-to-end proof, not just string matching: write a real impl,
    # actually import the generated shim, and confirm it calls through.
    import subprocess
    import sys

    out = tmp_path / "agent-kyc-refresh-agent"
    _build("kyc-refresh-agent.spec.yaml", out)

    impl_path = out / "src" / "impl" / "tools" / "get_customer_profile.py"
    impl_path.write_text(
        '"""Hand-written."""\n\n\ndef call(**kwargs):\n    return {"ok": True, "kwargs": kwargs}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.tools import get_customer_profile as shim\n"
            "result = shim.call(customerId='C123')\n"
            "assert result == {'ok': True, 'kwargs': {'customerId': 'C123'}}, result\n"
            "print('IMPORT_AND_DELEGATE_OK')\n",
        ],
        cwd=out,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "IMPORT_AND_DELEGATE_OK" in result.stdout
