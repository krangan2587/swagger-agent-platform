"""
Standard PyYAML discards position info once it builds Python objects.
We walk the composed Node tree ourselves so every value in the resulting
dict/list structure can be traced back to a line:column in the source file.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_spec.parser.location import SourceLocation

# Maps a "path" tuple (e.g. ("tools", 1, "sideEffects")) to where that
# value started in the source file.
LocationMap = dict[tuple, SourceLocation]


def load_yaml_with_locations(text: str, filename: str) -> tuple[object, LocationMap]:
    """Parse YAML text, returning (data, locations).

    Raises yaml.YAMLError (with a `.problem_mark`) on malformed syntax —
    callers turn that into a ParserError with a proper SourceLocation.
    """
    loader = yaml.SafeLoader(text)
    try:
        root_node = loader.get_single_node()
    finally:
        loader.dispose()

    locations: LocationMap = {}
    if root_node is None:
        return {}, locations

    data = _convert(root_node, loader, filename, (), locations)
    return data, locations


def _convert(node, loader: yaml.SafeLoader, filename: str, path: tuple, locations: LocationMap):
    locations[path] = SourceLocation(
        file=filename,
        line=node.start_mark.line + 1,
        column=node.start_mark.column + 1,
    )

    if isinstance(node, yaml.MappingNode):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=True)
            result[key] = _convert(value_node, loader, filename, path + (key,), locations)
        return result

    if isinstance(node, yaml.SequenceNode):
        return [
            _convert(item_node, loader, filename, path + (i,), locations)
            for i, item_node in enumerate(node.value)
        ]

    # ScalarNode
    return loader.construct_object(node, deep=True)


def load_yaml_file_with_locations(path: Path) -> tuple[object, LocationMap]:
    text = path.read_text(encoding="utf-8")
    return load_yaml_with_locations(text, str(path))
