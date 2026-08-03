from pathlib import Path

import pytest

from agent_spec.parser import ParserError, parse_spec_file

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def test_parses_valid_spec_into_typed_ast():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")

    assert ast.spec_version == "0.1"
    assert ast.info.name == "kyc-refresh-agent"
    assert ast.info.lifecycle == "pilot"
    assert len(ast.capabilities) == 2
    assert ast.capabilities[0].id == "summarize-kyc-gaps"
    assert len(ast.tools) == 2
    assert ast.tools[1].id == "update-kyc-record"
    assert ast.tools[1].side_effects == "write"
    assert ast.auth.credentials_ref == "secretsmanager://kyc-refresh-agent/creds"


def test_source_locations_are_attached():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")

    assert ast.info.source_location is not None
    assert ast.info.source_location.file.endswith("kyc-refresh-agent.spec.yaml")
    assert ast.info.source_location.line > 0

    assert ast.tools[0].source_location is not None
    assert ast.tools[1].source_location.line > ast.tools[0].source_location.line


def test_file_relative_ref_is_resolved_and_inlined():
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-with-refs.spec.yaml")

    cap = ast.capabilities[0]
    # The $ref is gone; the fragment's actual content is inlined.
    assert cap.inputs == {
        "type": "object",
        "required": ["customerId"],
        "properties": {
            "customerId": {"type": "string", "description": "Internal customer identifier"},
            "asOfDate": {"type": "string", "format": "date"},
        },
    }
    assert cap.outputs["required"] == ["gaps"]


def test_duplicate_id_raises_parser_error_with_location():
    with pytest.raises(ParserError) as exc_info:
        parse_spec_file(EXAMPLES_DIR / "duplicate-id.spec.yaml")

    err = exc_info.value
    assert "duplicate id" in err.message
    assert "get-customer-profile" in err.message
    assert err.location is not None
    assert err.location.line > 0


def test_malformed_yaml_raises_parser_error_with_location():
    with pytest.raises(ParserError) as exc_info:
        parse_spec_file(EXAMPLES_DIR / "malformed.spec.yaml")

    err = exc_info.value
    assert "malformed YAML" in err.message
    assert err.location is not None


def test_missing_file_raises_parser_error():
    with pytest.raises(ParserError):
        parse_spec_file(EXAMPLES_DIR / "does-not-exist.yaml")


def test_unresolved_ref_raises_parser_error(tmp_path):
    spec = tmp_path / "bad-ref.spec.yaml"
    spec.write_text(
        "specVersion: '0.1'\n"
        "info: { name: x, version: '1.0.0', owner: t, description: d, lifecycle: draft }\n"
        "capabilities:\n"
        "  - id: c1\n"
        "    description: d\n"
        "    inputs: { $ref: schemas/does-not-exist.json }\n"
        "    outputs: { type: object }\n"
    )
    with pytest.raises(ParserError) as exc_info:
        parse_spec_file(spec)
    assert "unresolved $ref" in exc_info.value.message
