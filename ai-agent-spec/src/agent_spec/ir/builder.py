"""
Stage 3 — IR Builder. Per Section 7.3:

Input:  the AST that passed Stage 2 validation
Output: an AgentIR object graph
Failure mode: IR construction should not fail for a spec that already
              passed validation -- if it does, that's a defect in the
              generator, not the spec.
"""

from __future__ import annotations

from agent_spec.ir.nodes import (
    AgentIR,
    AuthIR,
    CapabilityIR,
    DataContractIR,
    DeploymentIR,
    ErrorHandlingIR,
    GuardrailsIR,
    HumanInLoopIR,
    InfoIR,
    MemoryIR,
    ModelIR,
    ObservabilityIR,
    ToolIR,
)
from agent_spec.ir.schema_summary import summarize_json_schema
from agent_spec.parser.ast_nodes import AgentSpecAST

_WRITE_LIKE_SIDE_EFFECTS = frozenset({"write", "irreversible"})


def _norm(value):
    """Canonicalize an enum-like string to lower-kebab-case.

    A no-op for schema-valid specs, whose enums are already canonical --
    this exists so the IR Builder stays safe to call directly (e.g. from
    tests, or a future stage) without depending on Stage 2 having run
    first in the same process.
    """
    if isinstance(value, str):
        return value.strip().lower().replace("_", "-")
    return value


def _norm_list(values) -> list:
    return [_norm(v) for v in values] if values else []


class IRBuilder:
    def build(self, ast: AgentSpecAST) -> AgentIR:
        return AgentIR(
            spec_version=ast.spec_version,
            info=self._build_info(ast.info),
            capabilities=[self._build_capability(c) for c in ast.capabilities],
            tools=[self._build_tool(t, ast.auth) for t in ast.tools],
            data_contracts=[self._build_data_contract(dc) for dc in ast.data_contracts],
            model=self._build_model(ast.model),
            memory=self._build_memory(ast.memory) if ast.memory else None,
            guardrails=self._build_guardrails(ast.guardrails),
            auth=self._build_auth(ast.auth),
            human_in_loop=(
                self._build_human_in_loop(ast.human_in_loop) if ast.human_in_loop else None
            ),
            observability=self._build_observability(ast.observability),
            error_handling=self._build_error_handling(ast.error_handling),
            deployment=self._build_deployment(ast.deployment),
            requires_human_approval=self._compute_requires_human_approval(ast),
            source_file=ast.source_file,
        )

    # ---- derived fields --------------------------------------------------

    @staticmethod
    def _compute_requires_human_approval(ast: AgentSpecAST) -> bool:
        has_write_tool = any(
            _norm(tool.side_effects) in _WRITE_LIKE_SIDE_EFFECTS for tool in ast.tools
        )
        has_autonomy_ceiling = (
            ast.guardrails is not None and ast.guardrails.max_autonomy_steps is not None
        )
        return has_write_tool or has_autonomy_ceiling

    # ---- per-section builders ---------------------------------------------

    @staticmethod
    def _build_info(info) -> InfoIR:
        return InfoIR(
            name=info.name,
            version=info.version,
            owner=info.owner,
            description=info.description,
            lifecycle=_norm(info.lifecycle),
            tags=list(info.tags),
        )

    @staticmethod
    def _build_capability(cap) -> CapabilityIR:
        return CapabilityIR(
            id=cap.id,
            description=cap.description,
            inputs=cap.inputs,
            inputs_summary=summarize_json_schema(cap.inputs),
            outputs=cap.outputs,
            outputs_summary=summarize_json_schema(cap.outputs),
            scope_boundaries=cap.scope_boundaries,
            examples=list(cap.examples),
        )

    @staticmethod
    def _build_tool(tool, auth) -> ToolIR:
        # Direct link: resolve the tool's granted scopes right now, so
        # template code never has to chase authRef -> scopesPerTool itself.
        # Convention observed in the reference doc's example spec: scopesPerTool
        # is keyed by the tool's own id, not by the (looser) authRef label.
        auth_scopes = list(auth.scopes_per_tool.get(tool.id, [])) if auth else []

        retry_policy = tool.retry_policy
        if retry_policy is not None:
            retry_policy = {**retry_policy, "backoff": _norm(retry_policy.get("backoff"))}

        return ToolIR(
            id=tool.id,
            type=_norm(tool.type),
            description=tool.description,
            schema=tool.schema,
            side_effects=_norm(tool.side_effects),
            rate_limit=tool.rate_limit,
            auth_scopes=auth_scopes,
            timeout_ms=tool.timeout_ms,
            retry_policy=retry_policy,
        )

    @staticmethod
    def _build_data_contract(dc) -> DataContractIR:
        return DataContractIR(
            source=dc.source,
            classification=_norm(dc.classification),
            allowed_operations=_norm_list(dc.allowed_operations),
            retention=dc.retention,
            fields=list(dc.fields),
            pii_present=dc.pii_present,
        )

    @staticmethod
    def _build_model(model) -> ModelIR:
        return ModelIR(
            provider=model.provider,
            model=model.model,
            parameters=model.parameters,
            prompt_template_ref=model.prompt_template_ref,
            planning_strategy=_norm(model.planning_strategy),
            fallback_model=model.fallback_model,
        )

    @staticmethod
    def _build_memory(memory) -> MemoryIR:
        return MemoryIR(
            type=_norm(memory.type),
            scope=memory.scope,
            ttl=memory.ttl,
            persistence_ref=memory.persistence_ref,
            max_size_kb=memory.max_size_kb,
        )

    @staticmethod
    def _build_guardrails(g) -> GuardrailsIR:
        return GuardrailsIR(
            content_policies=list(g.content_policies),
            business_rules=list(g.business_rules),
            refusal_conditions=list(g.refusal_conditions),
            max_autonomy_steps=g.max_autonomy_steps,
            pii_handling=_norm(g.pii_handling),
        )

    @staticmethod
    def _build_auth(a) -> AuthIR:
        return AuthIR(
            identity_ref=a.identity_ref,
            credentials_ref=a.credentials_ref,
            scopes_per_tool=dict(a.scopes_per_tool),
            token_lifetime_seconds=a.token_lifetime_seconds,
        )

    @staticmethod
    def _build_human_in_loop(h) -> HumanInLoopIR:
        return HumanInLoopIR(
            checkpoints=list(h.checkpoints),
            escalation_path=h.escalation_path,
            override_authority=h.override_authority,
            approval_timeout_behavior=_norm(h.approval_timeout_behavior),
        )

    @staticmethod
    def _build_observability(o) -> ObservabilityIR:
        return ObservabilityIR(
            logging=o.logging,
            tracing=o.tracing,
            metrics=list(o.metrics),
            eval_suite_ref=o.eval_suite_ref,
        )

    @staticmethod
    def _build_error_handling(e) -> ErrorHandlingIR:
        return ErrorHandlingIR(
            on_tool_failure=_norm(e.on_tool_failure),
            on_timeout=_norm(e.on_timeout),
            on_low_confidence=_norm(e.on_low_confidence),
            fallback_response=e.fallback_response,
            confidence_threshold=e.confidence_threshold,
        )

    @staticmethod
    def _build_deployment(d) -> DeploymentIR:
        return DeploymentIR(
            environments=_norm_list(d.environments),
            rollout_strategy=_norm(d.rollout_strategy),
            compatibility=d.compatibility,
            change_history_ref=d.change_history_ref,
            approval_required=d.approval_required,
        )


def build_ir(ast: AgentSpecAST) -> AgentIR:
    """Convenience function — the entry point later stages and the CLI call."""
    return IRBuilder().build(ast)
