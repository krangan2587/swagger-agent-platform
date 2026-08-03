from __future__ import annotations

from agent_spec.parser.location import SourceLocation


class ParserError(Exception):
    """A Stage-1 failure: malformed syntax, an unresolved $ref, or a duplicate id.

    Per the reference doc (Section 7.1), these stop the pipeline before the
    Validator ever runs. Missing-field completeness is NOT a parser error —
    that's the schema Validator's job (Stage 2a).
    """

    def __init__(self, message: str, location: SourceLocation | None = None):
        self.message = message
        self.location = location
        prefix = f"{location}: " if location else ""
        super().__init__(f"{prefix}{message}")
