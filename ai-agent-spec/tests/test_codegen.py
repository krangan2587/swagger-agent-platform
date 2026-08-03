from pathlib import Path

import pytest

from agent_spec.codegen import (
    ManifestEntry,
    TargetAdapter,
    TemplateEngine,
    TemplateRenderError,
    get_target_adapter,
    list_target_adapters,
)
from agent_spec.ir import build_ir
from agent_spec.parser import parse_spec_file

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _render(spec_filename: str, target: str = "python-service") -> dict[str, str]:
    ast = parse_spec_file(EXAMPLES_DIR / spec_filename)
    ir = build_ir(ast)
    adapter = get_target_adapter(target)
    return TemplateEngine(adapter).render(ir)


def test_python_service_is_registered():
    assert "python-service" in list_target_adapters()


def test_unknown_target_raises_key_error():
    with pytest.raises(KeyError):
        get_target_adapter("not-a-real-target")


def test_generates_one_file_per_tool_and_capability():
    files = _render("kyc-refresh-agent.spec.yaml")

    assert "src/tools/get_customer_profile.py" in files
    assert "src/tools/update_kyc_record.py" in files
    assert "src/handlers/summarize_kyc_gaps.py" in files
    assert "src/handlers/draft_outreach_note.py" in files
    assert "src/guardrails/policy_hooks.py" in files
    assert "src/prompts/kyc_refresh.py" in files
    assert "src/memory/session_store.py" in files  # this spec declares memory


def test_kebab_case_ids_become_snake_case_filenames():
    # tool id 'get-customer-profile' -> file 'get_customer_profile.py'
    files = _render("kyc-refresh-agent.spec.yaml")
    assert "src/tools/get_customer_profile.py" in files
    assert "src/tools/get-customer-profile.py" not in files


def test_tool_binding_content_reflects_ir_fields():
    files = _render("kyc-refresh-agent.spec.yaml")
    content = files["src/tools/update_kyc_record.py"]

    assert 'TOOL_ID = "update-kyc-record"' in content
    assert 'SIDE_EFFECTS = "write"' in content
    assert "TIMEOUT_MS = 15000" in content
    assert "AUTH_SCOPES = ['kyc:write']" in content
    assert "RETRY_POLICY" in content
    assert "'backoff': 'exponential'" in content


def test_handler_content_includes_schema_summaries():
    files = _render("kyc-with-refs.spec.yaml")
    content = files["src/handlers/summarize_kyc_gaps.py"]

    assert "customerId" in content
    assert "gaps" in content


def test_guardrails_content_reflects_requires_human_approval():
    write_agent_files = _render("kyc-refresh-agent.spec.yaml")  # has a write tool
    read_only_files = _render("read-only-agent.spec.yaml")  # no write tool, no ceiling

    assert "REQUIRES_HUMAN_APPROVAL = True" in write_agent_files["src/guardrails/policy_hooks.py"]
    assert "REQUIRES_HUMAN_APPROVAL = False" in read_only_files["src/guardrails/policy_hooks.py"]


def test_memory_store_only_generated_when_memory_declared():
    with_memory = _render("memory-agent.spec.yaml")
    # kyc-refresh-agent.spec.yaml (Section 5 of the reference doc) DOES
    # declare memory -- read-only-agent.spec.yaml genuinely doesn't.
    without_memory = _render("read-only-agent.spec.yaml")

    assert "src/memory/session_store.py" in with_memory
    assert 'MEMORY_SCOPE = "user-id"' in with_memory["src/memory/session_store.py"]

    assert "src/memory/session_store.py" not in without_memory


def test_kyc_refresh_agent_also_declares_memory_and_gets_a_store():
    # Section 5's example spec includes memory (type: session, scope: case-id)
    files = _render("kyc-refresh-agent.spec.yaml")
    assert "src/memory/session_store.py" in files
    assert 'MEMORY_SCOPE = "case-id"' in files["src/memory/session_store.py"]


def test_post_process_ensures_trailing_newline():
    files = _render("kyc-refresh-agent.spec.yaml")
    for path, content in files.items():
        assert content.endswith("\n"), f"{path} does not end with a newline"


def test_unknown_predicate_raises_template_render_error(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "x.py.j2").write_text("x = 1\n")
    (tmp_path / "manifest.json").write_text(
        '[{"template": "x.py.j2", "output_path": "x.py", "when": "no_such_predicate"}]'
    )
    adapter = TargetAdapter(id="broken", template_pack_path=tmp_path)

    ast = parse_spec_file(EXAMPLES_DIR / "read-only-agent.spec.yaml")
    ir = build_ir(ast)

    with pytest.raises(TemplateRenderError) as exc_info:
        TemplateEngine(adapter).render(ir)
    assert "unknown predicate" in str(exc_info.value)


def test_iterate_over_without_item_name_raises_template_render_error(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "x.py.j2").write_text("x = 1\n")
    (tmp_path / "manifest.json").write_text(
        '[{"template": "x.py.j2", "output_path": "x_{{ loop.index0 }}.py", "iterate_over": "tools"}]'
    )
    adapter = TargetAdapter(id="broken2", template_pack_path=tmp_path)

    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")  # has tools
    ir = build_ir(ast)

    with pytest.raises(TemplateRenderError) as exc_info:
        TemplateEngine(adapter).render(ir)
    assert "item_name" in str(exc_info.value)


def test_undefined_ir_field_in_template_raises_template_render_error(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "x.py.j2").write_text("x = {{ ir.this_field_does_not_exist }}\n")
    (tmp_path / "manifest.json").write_text(
        '[{"template": "x.py.j2", "output_path": "x.py"}]'
    )
    adapter = TargetAdapter(id="broken3", template_pack_path=tmp_path)

    ast = parse_spec_file(EXAMPLES_DIR / "read-only-agent.spec.yaml")
    ir = build_ir(ast)

    with pytest.raises(TemplateRenderError):
        TemplateEngine(adapter).render(ir)


def test_manifest_entry_defaults():
    entry = ManifestEntry(template="t.j2", output_path="out.py")
    assert entry.iterate_over is None
    assert entry.item_name is None
    assert entry.when is None
