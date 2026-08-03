"""
The pluggable TargetAdapter interface from Section 7.6:

"A target adapter is the pluggable unit that defines 'what a target looks
like' to Stages 4 and 5. Adding a new target ... means implementing this
interface; it requires no change to the Parser, Validator, or IR Builder."

Compared to the doc's TypeScript sketch:

    interface TargetAdapter {
      id: string;
      templatePackPath: string;
      helpers: Record<string, (v: any) => string>;
      postProcess?(files, ir): files;
    }

this adds `predicates` -- named boolean checks a manifest entry can gate on
via `"when": "has_memory"` -- so conditional output files (like a memory
store binding that should only exist when the spec declares memory) don't
need arbitrary code embedded in the JSON manifest.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agent_spec.ir.nodes import AgentIR

PostProcessFn = Callable[[dict[str, str], AgentIR], dict[str, str]]


@dataclass
class ManifestEntry:
    template: str  # filename relative to templates_dir
    output_path: str  # a Jinja template string, e.g. "src/tools/{{ tool.id | snake_case }}.py"
    iterate_over: str | None = None  # name of a list attribute on AgentIR, e.g. "tools"
    item_name: str | None = None  # what the iterated item is called in the template context
    when: str | None = None  # name of a predicate registered on the adapter


@dataclass
class TargetAdapter:
    id: str
    template_pack_path: Path
    helpers: dict[str, Callable[[str], str]] = field(default_factory=dict)
    predicates: dict[str, Callable[[AgentIR], bool]] = field(default_factory=dict)
    post_process: PostProcessFn | None = None

    @property
    def templates_dir(self) -> Path:
        return self.template_pack_path / "templates"

    def load_manifest(self) -> list[ManifestEntry]:
        manifest_path = self.template_pack_path / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [ManifestEntry(**entry) for entry in raw]
