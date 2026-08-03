from pathlib import Path

from agent_spec.ir import build_ir, summarize_json_schema
from agent_spec.parser import parse_spec_file

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def test_ir_carries_over_basic_fields():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    ir = build_ir(ast)

    assert ir.spec_version == "0.1"
    assert ir.info.name == "kyc-refresh-agent"
    assert len(ir.tools) == 2
    assert len(ir.capabilities) == 2


def test_enum_normalization_is_idempotent_on_already_canonical_values():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    ir = build_ir(ast)

    assert ir.info.lifecycle == "pilot"
    assert ir.model.planning_strategy == "plan-execute"
    assert ir.tools[1].side_effects == "write"
    assert ir.deployment.rollout_strategy == "canary"


def test_enum_normalization_canonicalizes_odd_casing():
    # Build IR directly from a hand-built AST (bypassing schema validation,
    # which is exactly why _norm() exists as a defensive no-op/fixup).
    from agent_spec.parser.ast_nodes import AgentSpecAST, InfoNode, ToolNode

    ast = AgentSpecAST(
        info=InfoNode(lifecycle="  Production  "),
        tools=[ToolNode(id="t1", side_effects="WRITE", type="MCP")],
    )
    ir = build_ir(ast)

    assert ir.info.lifecycle == "production"
    assert ir.tools[0].side_effects == "write"
    assert ir.tools[0].type == "mcp"


def test_auth_scopes_resolved_as_direct_link_on_tool():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    ir = build_ir(ast)

    by_id = {t.id: t for t in ir.tools}
    assert by_id["get-customer-profile"].auth_scopes == ["kyc:read"]
    assert by_id["update-kyc-record"].auth_scopes == ["kyc:write"]


def test_tool_with_no_scopes_entry_gets_empty_list_not_a_crash():
    ast = parse_spec_file(EXAMPLES_DIR / "policy-violation-checkpoints.spec.yaml")
    ir = build_ir(ast)
    assert ir.tools[0].auth_scopes == []


def test_capability_schema_summaries_are_target_neutral():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-with-refs.spec.yaml")
    ir = build_ir(ast)

    cap = ir.capabilities[0]
    # inputs came in via a $ref to schemas/kyc-input.json, required: [customerId]
    assert "customerId:" in cap.inputs_summary  # required (no "?")
    assert "asOfDate?:" in cap.inputs_summary  # optional
    assert cap.outputs_summary == "{ gaps: array }"


def test_summarize_json_schema_variants():
    assert summarize_json_schema(None) == "any"
    assert summarize_json_schema({}) == "any"
    assert summarize_json_schema({"type": "string"}) == "string"
    assert summarize_json_schema({"type": "array", "items": {"type": "string"}}) == "array<string>"
    assert summarize_json_schema({"type": "object"}) == "object"
    assert summarize_json_schema(
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    ) == "{ a: string }"


def test_requires_human_approval_true_when_write_tool_present():
    # kyc-refresh-agent has update-kyc-record with sideEffects: write
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    ir = build_ir(ast)
    assert ir.requires_human_approval is True


def test_requires_human_approval_false_for_read_only_no_ceiling():
    ast = parse_spec_file(EXAMPLES_DIR / "read-only-agent.spec.yaml")
    ir = build_ir(ast)
    assert ir.requires_human_approval is False


def test_requires_human_approval_true_from_autonomy_ceiling_alone():
    from agent_spec.parser.ast_nodes import AgentSpecAST, GuardrailsNode, ToolNode

    ast = AgentSpecAST(
        tools=[ToolNode(id="t1", side_effects="read")],
        guardrails=GuardrailsNode(max_autonomy_steps=5),
    )
    ir = build_ir(ast)
    assert ir.requires_human_approval is True


def test_ir_builder_never_raises_on_a_validated_spec():
    # Section 7.3: "IR construction should not fail for a spec that already
    # passed validation." Smoke-test every example that's supposed to be
    # fully valid.
    for filename in ("kyc-refresh-agent.spec.yaml", "kyc-with-refs.spec.yaml", "read-only-agent.spec.yaml"):
        ast = parse_spec_file(EXAMPLES_DIR / filename)
        build_ir(ast)  # must not raise
