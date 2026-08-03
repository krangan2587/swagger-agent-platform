"""
Step 1 of the build plan: standalone schema validation.

Loads a spec file (YAML or JSON), checks it against the formal JSON Schema
(Appendix A of the reference doc), and reports pass/fail with located errors.

This module does ONLY schema validation (Stage 2a in the pipeline design).
Policy validation (Stage 2b - cross-field business rules) comes in Step 3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_PATH = Path(__file__).parent / "schema" / "agent_spec_schema.json"


@dataclass
class SchemaError:
    """One validation failure, with enough context to act on it."""

    message: str
    path: str  # dotted/bracket path into the document, e.g. "tools[1].sideEffects"

    def __str__(self) -> str:
        location = self.path or "<document root>"
        return f"{location}: {self.message}"


@dataclass
class ValidationReport:
    """Mirrors the ValidationReport shape described in Section 7.2 of the reference doc."""

    valid: bool
    errors: list[SchemaError] = field(default_factory=list)
    warnings: list[SchemaError] = field(default_factory=list)

    def print_summary(self) -> None:
        if self.valid:
            print("✅ Spec is schema-valid.")
            return
        print(f"❌ Spec failed schema validation ({len(self.errors)} error(s)):\n")
        for err in self.errors:
            print(f"  - {err}")


def _load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_spec_file(path: Path) -> dict[str, Any]:
    """Load a spec file, detecting YAML vs JSON by extension."""
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)

    # Fallback: try YAML first (it's a superset of JSON), as the reference
    # doc's Parser design (Section 7.1) does.
    return yaml.safe_load(text)


def _error_path(err: ValidationError) -> str:
    """Turn jsonschema's deque path into a readable dotted/bracket path."""
    parts: list[str] = []
    for p in err.absolute_path:
        if isinstance(p, int):
            parts[-1] = f"{parts[-1]}[{p}]" if parts else f"[{p}]"
        else:
            parts.append(str(p))
    return ".".join(parts) if parts else ""


def validate_schema(spec: dict[str, Any]) -> ValidationReport:
    """Validate an already-loaded spec dict against the AgentSpec JSON Schema."""
    schema = _load_schema()
    validator = Draft202012Validator(schema)

    errors = [
        SchemaError(message=e.message, path=_error_path(e))
        for e in sorted(validator.iter_errors(spec), key=lambda e: _error_path(e))
    ]
    return ValidationReport(valid=len(errors) == 0, errors=errors)


def validate_spec_file(path: str | Path) -> ValidationReport:
    """Load a spec file from disk and validate it against the schema.

    This is the entry point the `validate-spec` CLI command calls.
    """
    spec = _load_spec_file(Path(path))
    return validate_schema(spec)
