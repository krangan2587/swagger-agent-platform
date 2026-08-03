"""
Stage 2 — Validator, both passes combined, per Section 7.2:

"Any schema or policy error sets valid: false. The pipeline stops; in CI
this surfaces as a required check failure blocking merge."

Schema validation (2a) runs on the raw parsed document. Policy validation
(2b) needs the typed AST from the Parser (Stage 1). The two are kept as
genuinely separate modules (Steps 1 and 3 of this build) — this module
just runs both and merges the results into one report, exactly as the
doc's ValidationReport does conceptually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_spec.parser import ParserError, parse_spec_file
from agent_spec.policy import PolicyError, validate_policy
from agent_spec.validator import SchemaError, validate_spec_file


@dataclass
class Stage2Report:
    valid: bool
    schema_errors: list[SchemaError] = field(default_factory=list)
    policy_errors: list[PolicyError] = field(default_factory=list)
    # Set only if the Parser itself couldn't build an AST (Stage 1 failure),
    # in which case policy checks (which need the AST) couldn't run at all.
    parser_error: str | None = None

    def print_summary(self) -> None:
        if self.valid:
            print("✅ Spec passes schema validation and all policy rules.")
            return

        print("❌ Spec failed Stage 2 validation.\n")

        if self.schema_errors:
            print(f"Schema errors ({len(self.schema_errors)}):")
            for e in self.schema_errors:
                print(f"  - {e}")
            print()

        if self.parser_error:
            print(f"Could not build an AST, so policy rules could not run:")
            print(f"  - {self.parser_error}\n")

        if self.policy_errors:
            print(f"Policy errors ({len(self.policy_errors)}):")
            for e in self.policy_errors:
                print(f"  - {e}")


def run_stage2(path: str | Path) -> Stage2Report:
    schema_report = validate_spec_file(path)

    policy_errors: list[PolicyError] = []
    parser_error: str | None = None
    try:
        ast = parse_spec_file(path)
        policy_errors = validate_policy(ast).errors
    except ParserError as e:
        parser_error = str(e)

    valid = schema_report.valid and not policy_errors and parser_error is None
    return Stage2Report(
        valid=valid,
        schema_errors=schema_report.errors,
        policy_errors=policy_errors,
        parser_error=parser_error,
    )
