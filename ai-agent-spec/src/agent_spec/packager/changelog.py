from __future__ import annotations


def render_changelog(agent_name: str, history: list[dict]) -> str:
    """Renders CHANGELOG.md from the full version history recorded in the
    registry, newest first -- per Section 7.5 step 4."""
    lines = [f"# Changelog — {agent_name}", ""]

    if not history:
        lines.append("_No versions recorded yet._")
        return "\n".join(lines) + "\n"

    for entry in reversed(history):
        lines.append(f"## {entry['version']} — {entry['date']}")
        lines.append("")
        lines.append(f"- {entry['notes']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
