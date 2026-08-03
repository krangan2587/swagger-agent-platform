from pathlib import Path

from agent_spec.parser import parse_spec_file
from agent_spec.pipeline import run_stage2
from agent_spec.policy import validate_policy

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _rule_ids(errors) -> set[str]:
    return {e.rule_id for e in errors}


def test_compliant_spec_passes_every_rule():
    # Section 5 of the reference doc: "internally consistent with every
    # rule in Section 4 and Section 7.2, including the conditional
    # requirements."
    ast = parse_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    report = validate_policy(ast)
    assert report.valid is True
    assert report.errors == []


def test_write_tool_without_checkpoints_fails():
    ast = parse_spec_file(EXAMPLES_DIR / "policy-violation-checkpoints.spec.yaml")
    report = validate_policy(ast)

    assert report.valid is False
    assert "require-checkpoints-for-write-effects" in _rule_ids(report.errors)
    err = next(e for e in report.errors if e.rule_id == "require-checkpoints-for-write-effects")
    assert "update-something" in err.message
    assert err.location is not None


def test_pii_without_handling_fails():
    ast = parse_spec_file(EXAMPLES_DIR / "policy-violation-pii.spec.yaml")
    report = validate_policy(ast)

    assert report.valid is False
    assert "require-pii-handling-for-pii-data" in _rule_ids(report.errors)


def test_restricted_data_with_unapproved_provider_fails():
    ast = parse_spec_file(EXAMPLES_DIR / "policy-violation-restricted-provider.spec.yaml")
    report = validate_policy(ast)

    assert report.valid is False
    assert "restricted-data-requires-approved-provider" in _rule_ids(report.errors)
    err = next(
        e for e in report.errors if e.rule_id == "restricted-data-requires-approved-provider"
    )
    assert "some-unapproved-vendor" in err.message


def test_production_without_approval_fails():
    ast = parse_spec_file(EXAMPLES_DIR / "policy-violation-production-approval.spec.yaml")
    report = validate_policy(ast)

    assert report.valid is False
    assert "production-requires-deployment-approval" in _rule_ids(report.errors)


def test_bad_credentials_ref_fails_even_when_schema_also_catches_it():
    # invalid-example.spec.yaml (from Step 1) has a literal credentialsRef.
    # The schema pattern catches it too -- this proves the policy layer
    # is an independent, defense-in-depth check, not a duplicate no-op.
    ast = parse_spec_file(EXAMPLES_DIR / "invalid-example.spec.yaml")
    report = validate_policy(ast)

    assert "credentials-ref-must-be-secret-manager-reference" in _rule_ids(report.errors)


def test_each_violation_fixture_trips_exactly_its_own_rule():
    # Fixtures are schema-valid and constructed to isolate one rule each --
    # this pins that down so a fixture change can't silently start
    # tripping a different rule than intended.
    cases = {
        "policy-violation-checkpoints.spec.yaml": "require-checkpoints-for-write-effects",
        "policy-violation-pii.spec.yaml": "require-pii-handling-for-pii-data",
        "policy-violation-restricted-provider.spec.yaml": "restricted-data-requires-approved-provider",
        "policy-violation-production-approval.spec.yaml": "production-requires-deployment-approval",
    }
    for filename, expected_rule in cases.items():
        ast = parse_spec_file(EXAMPLES_DIR / filename)
        report = validate_policy(ast)
        assert _rule_ids(report.errors) == {expected_rule}, filename


# --- Stage 2 pipeline (schema + policy combined) -------------------------


def test_stage2_passes_for_fully_compliant_spec():
    report = run_stage2(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    assert report.valid is True
    assert report.schema_errors == []
    assert report.policy_errors == []
    assert report.parser_error is None


def test_stage2_reports_both_schema_and_policy_errors_independently():
    # invalid-example.spec.yaml is both schema-invalid (missing sideEffects,
    # bad lifecycle enum) AND policy-invalid (bad credentialsRef pattern).
    report = run_stage2(EXAMPLES_DIR / "invalid-example.spec.yaml")

    assert report.valid is False
    assert len(report.schema_errors) > 0
    assert len(report.policy_errors) > 0
    assert report.parser_error is None  # it parses fine, just fails both checks


def test_stage2_reports_parser_error_when_ast_cannot_be_built():
    # duplicate-id.spec.yaml is schema-valid (jsonschema doesn't know about
    # id-uniqueness) but the Parser rejects it, so policy checks never run.
    report = run_stage2(EXAMPLES_DIR / "duplicate-id.spec.yaml")

    assert report.valid is False
    assert report.schema_errors == []
    assert report.policy_errors == []
    assert report.parser_error is not None
    assert "duplicate id" in report.parser_error
