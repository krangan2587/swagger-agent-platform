"""
A minimal stand-in for the "Agent Registry" governance component the
reference doc mentions elsewhere (Section 3's cross-cutting governance
plane; Section 7.5 step 4: "diffing info.version against the last version
recorded in the agent registry"). A real registry is a separate,
centrally-run service (Section 17 of the design deck) -- this is a local
JSON file, so CHANGELOG generation has something concrete to diff against
without standing up that service.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_registry(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(path: Path, data: dict[str, list[dict]]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_history(data: dict[str, list[dict]], agent_name: str) -> list[dict]:
    return list(data.get(agent_name, []))


def record_version(
    data: dict[str, list[dict]],
    agent_name: str,
    version: str,
    date_str: str,
    notes: str,
) -> tuple[dict[str, list[dict]], bool]:
    """Append a new version entry, unless this exact version is already the
    most recently recorded one (regenerating the same version is a no-op,
    not a new changelog entry). Returns (updated_data, was_new_entry_added).
    """
    history = list(data.get(agent_name, []))
    if history and history[-1]["version"] == version:
        return data, False

    history.append({"version": version, "date": date_str, "notes": notes})
    updated = dict(data)
    updated[agent_name] = history
    return updated, True
