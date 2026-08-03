"""
Produces a short, target-neutral description of a JSON Schema fragment --
"a simplified, target-neutral type description for every capability's
inputs/outputs" per Section 7.3. Not a full JSON Schema renderer; just
enough for docs and template scaffolding to show a human what shape of
data is expected without every target adapter re-parsing the schema itself.
"""

from __future__ import annotations


def summarize_json_schema(schema: dict | None) -> str:
    if not schema:
        return "any"

    schema_type = schema.get("type")

    if schema_type == "object":
        properties = schema.get("properties") or {}
        if not properties:
            return "object"
        required = set(schema.get("required", []))
        parts = []
        for name, subschema in properties.items():
            sub_type = subschema.get("type", "any") if isinstance(subschema, dict) else "any"
            marker = "" if name in required else "?"
            parts.append(f"{name}{marker}: {sub_type}")
        return "{ " + ", ".join(parts) + " }"

    if schema_type == "array":
        items = schema.get("items") or {}
        item_type = items.get("type", "any") if isinstance(items, dict) else "any"
        return f"array<{item_type}>"

    if schema_type:
        return str(schema_type)

    return "any"
