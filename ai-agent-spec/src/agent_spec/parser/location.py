"""Where a piece of data came from, so downstream errors can point at it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int  # 1-indexed
    column: int  # 1-indexed

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"
