"""Generated memory store binding.

DO NOT EDIT BY HAND -- generated from the agent spec's memory section by the
Template Engine (Stage 4, target: python-service). This file only exists
because the spec declared a memory section other than "none".
"""

from __future__ import annotations

MEMORY_TYPE = "long-term"
MEMORY_SCOPE = "case-id"
MEMORY_TTL = "2555d"
PERSISTENCE_REF = "store://fraud-case-memory"


def get(key: str):
    """Fetch a value scoped by MEMORY_SCOPE ('case-id')."""
    # TODO: back this with your session/long-term store.
    raise NotImplementedError


def set(key: str, value) -> None:
    """Store a value scoped by MEMORY_SCOPE, honoring MEMORY_TTL if set."""
    # TODO: back this with your session/long-term store.
    raise NotImplementedError
