"""
The python-service target adapter (Section 7.6). This is one concrete
TargetAdapter -- adding a second target (e.g. TypeScript/Node) means
writing a sibling package with its own manifest.json + templates/, then
registering it in codegen/registry.py. No other stage changes.
"""

from __future__ import annotations

from pathlib import Path

from agent_spec.codegen.helpers import DEFAULT_HELPERS
from agent_spec.codegen.target_adapter import TargetAdapter
from agent_spec.ir.nodes import AgentIR

_PACK_DIR = Path(__file__).parent


def _ensure_trailing_newline(files: dict[str, str], ir: AgentIR) -> dict[str, str]:
    """A minimal postProcess example (Section 7.6): 'lets an adapter make a
    final pass over rendered files ... after templating but before
    packaging' -- e.g. running a real code formatter. This stands in for
    that without adding a formatter dependency: it just guarantees every
    generated file ends with exactly one trailing newline."""
    return {
        path: (content if content.endswith("\n") else content + "\n")
        for path, content in files.items()
    }


ADAPTER = TargetAdapter(
    id="python-service",
    template_pack_path=_PACK_DIR,
    helpers=dict(DEFAULT_HELPERS),
    predicates={
        "has_memory": lambda ir: ir.memory is not None,
        "has_human_in_loop": lambda ir: ir.human_in_loop is not None,
    },
    post_process=_ensure_trailing_newline,
)
