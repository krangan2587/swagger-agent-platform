"""
Case-conversion helpers, registered as Jinja filters. These are the
"adapter-supplied helper functions such as case conversion" mentioned in
Section 7.4, step 3 -- templates use them as `{{ tool.id | snake_case }}`,
exactly matching the manifest example in Section 7.4.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")
_WORD_BOUNDARY = re.compile(r"[-_\s]+")


def _words(s: str) -> list[str]:
    """Split an identifier into lowercase words, regardless of its
    original casing convention (kebab-case, snake_case, camelCase, ...)."""
    s = _CAMEL_BOUNDARY.sub("_", s)
    return [w for w in _WORD_BOUNDARY.split(s) if w]


def snake_case(s: str) -> str:
    return "_".join(w.lower() for w in _words(s))


def kebab_case(s: str) -> str:
    return "-".join(w.lower() for w in _words(s))


def pascal_case(s: str) -> str:
    return "".join(w.capitalize() for w in _words(s))


def camel_case(s: str) -> str:
    words = _words(s)
    if not words:
        return s
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def ref_stem(ref: str | None) -> str:
    """'prompts/kyc-refresh.md' -> 'kyc-refresh'. Used to derive an output
    filename from a *Ref field without the directory or extension."""
    if not ref:
        return "prompt"
    return PurePosixPath(ref).stem


DEFAULT_HELPERS = {
    "snake_case": snake_case,
    "kebab_case": kebab_case,
    "pascal_case": pascal_case,
    "camel_case": camel_case,
    "ref_stem": ref_stem,
}
