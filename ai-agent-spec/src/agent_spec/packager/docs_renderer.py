"""
Stage 5's reference documentation generator. Per Section 7.5, step 2:

"Generate reference documentation (docs/reference.html) directly from the
IR using a small data-driven renderer -- not a template -- the same way an
OpenAPI/Swagger UI page is generated live from a spec rather than
hand-authored."

That's a deliberate distinction from Stage 4's Jinja templates: this module
builds the HTML directly in Python by walking the IR's data, so there's no
separate .html file that could drift out of sync with what AgentIR actually
contains.
"""

from __future__ import annotations

from html import escape

from agent_spec.ir.nodes import AgentIR


def _table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return "<p><em>none</em></p>"
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _list_items(items: dict[str, str]) -> str:
    return "".join(f"<li><strong>{escape(k)}:</strong> {escape(v)}</li>" for k, v in items.items())


_STYLE = """
  body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px;
         margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }
  h1 { border-bottom: 2px solid #ddd; padding-bottom: .5rem; }
  h2 { margin-top: 2rem; color: #333; }
  table { border-collapse: collapse; width: 100%; margin: .5rem 0 1.5rem; }
  th, td { border: 1px solid #ddd; padding: .4rem .6rem; text-align: left; font-size: .9rem; }
  th { background: #f5f5f5; }
  .badge { display: inline-block; background: #eef2ff; border-radius: 4px;
           padding: .1rem .6rem; font-size: .8rem; margin-right: .3rem; }
  code { background: #f5f5f5; padding: .1rem .3rem; border-radius: 3px; }
  footer { color: #888; font-size: .85rem; margin-top: 3rem; }
"""


def render_reference_html(ir: AgentIR) -> str:
    info = ir.info

    capability_rows = [
        [c.id, c.description, c.inputs_summary, c.outputs_summary, c.scope_boundaries or "—"]
        for c in ir.capabilities
    ]
    tool_rows = [
        [t.id, t.type, t.side_effects, ", ".join(t.auth_scopes) or "—", t.timeout_ms]
        for t in ir.tools
    ]
    data_contract_rows = [
        [dc.source, dc.classification, ", ".join(dc.allowed_operations), dc.retention, dc.pii_present]
        for dc in ir.data_contracts
    ]

    memory_html = ""
    if ir.memory:
        memory_html = f"""
<h2>Memory</h2>
<ul>{_list_items({
    "Type": ir.memory.type,
    "Scope": ir.memory.scope or "—",
    "TTL": ir.memory.ttl or "—",
})}</ul>"""

    hil_html = ""
    if ir.human_in_loop:
        h = ir.human_in_loop
        hil_html = f"""
<h2>Human in the Loop</h2>
<ul>{_list_items({
    "Checkpoints": ", ".join(h.checkpoints) or "—",
    "Escalation path": h.escalation_path or "—",
    "Override authority": h.override_authority or "—",
    "Approval timeout behavior": h.approval_timeout_behavior,
})}</ul>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(info.name or "Agent")} — Reference</title>
<style>{_STYLE}</style>
</head>
<body>

<h1>{escape(info.name or "Agent")}
  <span class="badge">v{escape(info.version or "?")}</span>
  <span class="badge">{escape(info.lifecycle or "?")}</span>
</h1>
<p>{escape(info.description or "")}</p>
<ul>{_list_items({
    "Owner": info.owner or "—",
    "Tags": ", ".join(info.tags) or "—",
    "Human approval required": str(ir.requires_human_approval),
})}</ul>

<h2>Capabilities</h2>
{_table(["id", "description", "inputs", "outputs", "scope boundaries"], capability_rows)}

<h2>Tools</h2>
{_table(["id", "type", "side effects", "auth scopes", "timeout (ms)"], tool_rows)}

<h2>Data Contracts</h2>
{_table(["source", "classification", "allowed operations", "retention", "PII present"], data_contract_rows)}

<h2>Model</h2>
<ul>{_list_items({
    "Provider": ir.model.provider or "—",
    "Model": ir.model.model or "—",
    "Planning strategy": ir.model.planning_strategy or "—",
    "Prompt template ref": ir.model.prompt_template_ref or "—",
})}</ul>
{memory_html}
<h2>Guardrails</h2>
<ul>{_list_items({
    "Content policies": ", ".join(ir.guardrails.content_policies) or "—",
    "Refusal conditions": ", ".join(ir.guardrails.refusal_conditions) or "—",
    "Max autonomy steps": str(ir.guardrails.max_autonomy_steps) if ir.guardrails.max_autonomy_steps is not None else "—",
    "PII handling": ir.guardrails.pii_handling or "—",
})}</ul>
{hil_html}
<h2>Deployment</h2>
<ul>{_list_items({
    "Environments": ", ".join(ir.deployment.environments) or "—",
    "Rollout strategy": ir.deployment.rollout_strategy or "—",
    "Approval required": str(ir.deployment.approval_required),
})}</ul>

<footer>Generated live from the agent's IR by the Output Packager (Stage 5) —
this page cannot drift from what was actually built.</footer>
</body>
</html>
"""
