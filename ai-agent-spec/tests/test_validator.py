from pathlib import Path

from agent_spec.validator import validate_spec_file

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def test_valid_spec_passes():
    report = validate_spec_file(EXAMPLES_DIR / "kyc-refresh-agent.spec.yaml")
    assert report.valid is True
    assert report.errors == []


def test_invalid_spec_fails_with_expected_errors():
    report = validate_spec_file(EXAMPLES_DIR / "invalid-example.spec.yaml")
    assert report.valid is False

    error_paths = {e.path for e in report.errors}
    error_text = " ".join(e.message for e in report.errors)

    # (1) bad enum value on info.lifecycle
    assert "info.lifecycle" in error_paths

    # (2) missing required field on tools[0]
    assert any("sideEffects" in e.message for e in report.errors)

    # (3) credentialsRef pattern violation
    assert "auth.credentialsRef" in error_paths
    assert "does not match" in error_text or "pattern" in error_text


def test_missing_file_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        validate_spec_file(EXAMPLES_DIR / "does-not-exist.yaml")
