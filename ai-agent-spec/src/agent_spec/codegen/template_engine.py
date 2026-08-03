"""
Stage 4 — Template Engine. Per Section 7.4:

Input:  the AgentIR from Stage 3, plus a selected target adapter's
        template pack and manifest
Output: an in-memory virtual file set: Map<relativePath, renderedContent>.
        Nothing is written to disk yet.
Failure mode: a template rendering error fails that target's generation
        and is reported with the manifest entry and IR path involved.
"""

from __future__ import annotations

import jinja2

from agent_spec.codegen.helpers import DEFAULT_HELPERS
from agent_spec.codegen.target_adapter import ManifestEntry, TargetAdapter
from agent_spec.ir.nodes import AgentIR


class TemplateRenderError(Exception):
    def __init__(self, entry: ManifestEntry, detail: str):
        self.entry = entry
        self.detail = detail
        super().__init__(f"[{entry.template}] {detail}")


class TemplateEngine:
    def __init__(self, adapter: TargetAdapter):
        self.adapter = adapter
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(adapter.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,  # fail loudly on a typo'd IR field
        )
        for name, fn in {**DEFAULT_HELPERS, **adapter.helpers}.items():
            self.env.filters[name] = fn

    def render(self, ir: AgentIR) -> dict[str, str]:
        """Run every manifest entry against the IR and collect the results.
        Step 3, from the doc: 'For each manifest entry, render its template
        against the IR (and, if the entry has iterateOver, once per item in
        that IR collection).' Step 4: 'Collect every rendered output in
        memory as a virtual file set.'"""
        virtual_files: dict[str, str] = {}

        for entry in self.adapter.load_manifest():
            if entry.when is not None and not self._predicate_holds(entry.when, ir):
                continue
            self._render_entry(entry, ir, virtual_files)

        if self.adapter.post_process:
            virtual_files = self.adapter.post_process(virtual_files, ir)

        return virtual_files

    def _predicate_holds(self, name: str, ir: AgentIR) -> bool:
        predicate = self.adapter.predicates.get(name)
        if predicate is None:
            raise TemplateRenderError(
                ManifestEntry(template="<manifest>", output_path="", when=name),
                f"unknown predicate '{name}' referenced by a manifest entry's 'when'",
            )
        return predicate(ir)

    def _render_entry(
        self, entry: ManifestEntry, ir: AgentIR, virtual_files: dict[str, str]
    ) -> None:
        try:
            template = self.env.get_template(entry.template)
            output_path_template = self.env.from_string(entry.output_path)
        except jinja2.TemplateError as e:
            raise TemplateRenderError(entry, f"could not load template: {e}") from e

        if entry.iterate_over:
            if not entry.item_name:
                raise TemplateRenderError(
                    entry, "manifest entry sets iterate_over but not item_name"
                )
            items = getattr(ir, entry.iterate_over, None) or []
            for item in items:
                context = {"ir": ir, entry.item_name: item}
                self._render_one(template, output_path_template, context, entry, virtual_files)
        else:
            context = {"ir": ir}
            self._render_one(template, output_path_template, context, entry, virtual_files)

    @staticmethod
    def _render_one(template, output_path_template, context, entry, virtual_files):
        try:
            content = template.render(**context)
            output_path = output_path_template.render(**context)
        except jinja2.TemplateError as e:
            raise TemplateRenderError(entry, str(e)) from e
        virtual_files[output_path] = content
