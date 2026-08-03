"""
Resolves every {"$ref": "..."} object in a parsed spec, per Section 7.1:

- Local pointers:        {"$ref": "#/capabilities/0"}
- File-relative fragments: {"$ref": "schemas/kyc-input.json"}

By the time resolve_refs() returns, nothing in the tree has a $ref left —
everything is inlined, exactly as Section 7.1's design notes describe:
"no later stage needs to know the difference between an inline schema
and a $ref."
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from agent_spec.parser.errors import ParserError
from agent_spec.parser.location import SourceLocation
from agent_spec.parser.yaml_loader import LocationMap, load_yaml_with_locations


def resolve_refs(
    node: object,
    root: object,
    base_dir: Path,
    locations: LocationMap,
    path: tuple = (),
    seen: frozenset[str] = frozenset(),
) -> object:
    """Recursively resolve $ref entries. `root` stays fixed (the top-level
    document) so local pointers can always be resolved, even deep inside
    nested structures."""

    if isinstance(node, dict):
        if list(node.keys()) == ["$ref"] and isinstance(node["$ref"], str):
            return _resolve_single_ref(node["$ref"], root, base_dir, locations, path, seen)
        return {
            key: resolve_refs(value, root, base_dir, locations, path + (key,), seen)
            for key, value in node.items()
        }

    if isinstance(node, list):
        return [
            resolve_refs(item, root, base_dir, locations, path + (i,), seen)
            for i, item in enumerate(node)
        ]

    return node


def _resolve_single_ref(
    ref: str,
    root: object,
    base_dir: Path,
    locations: LocationMap,
    path: tuple,
    seen: frozenset[str],
) -> object:
    if ref in seen:
        raise ParserError(f"circular $ref detected: '{ref}'", locations.get(path))
    next_seen = seen | {ref}

    if ref.startswith("#/"):
        target = _json_pointer_lookup(root, ref, locations, path)
        # Local-pointer targets are resolved in-place against the same root/base_dir.
        return resolve_refs(target, root, base_dir, locations, path, next_seen)

    # File-relative fragment reference.
    frag_path = (base_dir / ref).resolve()
    if not frag_path.exists():
        raise ParserError(
            f"unresolved $ref: '{ref}' (no such file: {frag_path})", locations.get(path)
        )

    if frag_path.suffix.lower() in (".yaml", ".yml"):
        frag_data, frag_locations = load_yaml_with_locations(
            frag_path.read_text(encoding="utf-8"), str(frag_path)
        )
    elif frag_path.suffix.lower() == ".json":
        try:
            frag_data = json.loads(frag_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            loc = SourceLocation(str(frag_path), e.lineno, e.colno)
            raise ParserError(f"malformed JSON in referenced fragment: {e.msg}", loc) from e
        frag_locations = {}
    else:
        raise ParserError(
            f"unsupported $ref target extension: '{frag_path.suffix}' (want .yaml/.yml/.json)",
            locations.get(path),
        )

    # A fragment can itself contain $refs, resolved relative to *its own* directory.
    return resolve_refs(frag_data, frag_data, frag_path.parent, frag_locations, (), next_seen)


def _json_pointer_lookup(root: object, ref: str, locations: LocationMap, path: tuple) -> object:
    """Minimal RFC 6901 JSON Pointer resolution against the root document."""
    pointer = ref[2:]  # strip leading "#/"
    current = root
    for raw_token in pointer.split("/") if pointer else []:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as e:
                raise ParserError(
                    f"unresolved $ref: '{ref}' (bad index '{token}')", locations.get(path)
                ) from e
        elif isinstance(current, dict):
            if token not in current:
                raise ParserError(
                    f"unresolved $ref: '{ref}' (no key '{token}')", locations.get(path)
                )
            current = current[token]
        else:
            raise ParserError(
                f"unresolved $ref: '{ref}' (cannot descend into scalar at '{token}')",
                locations.get(path),
            )
    return current
