"""
Registry of available target adapters. Per Section 7.6: "New adapters
register through a plugin registry -- either a directory convention the
generator scans on startup, or an explicit list in generator configuration."
We use the explicit-list form here; it's the simpler of the two and
sufficient until a second real target exists.
"""

from __future__ import annotations

from agent_spec.codegen.target_adapter import TargetAdapter
from agent_spec.codegen.targets.python_service.adapter import ADAPTER as PYTHON_SERVICE_ADAPTER

_ADAPTERS: dict[str, TargetAdapter] = {
    PYTHON_SERVICE_ADAPTER.id: PYTHON_SERVICE_ADAPTER,
}


def get_target_adapter(target_id: str) -> TargetAdapter:
    if target_id not in _ADAPTERS:
        raise KeyError(target_id)
    return _ADAPTERS[target_id]


def list_target_adapters() -> list[str]:
    return sorted(_ADAPTERS.keys())


def register_target_adapter(adapter: TargetAdapter) -> None:
    """Extension point (Section 7.6): a business line adds its own target
    (or overrides a built-in one) by constructing a TargetAdapter and
    calling this -- no change to any earlier stage required."""
    _ADAPTERS[adapter.id] = adapter
