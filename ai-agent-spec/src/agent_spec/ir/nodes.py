"""
Stage 3 output types — one dataclass per section, mirroring the AST but
normalized. Per Section 7.3's design notes, the IR has no concept of $ref
(already inlined by the Parser), enum values are canonical, cross-references
are direct links, and derived fields are precomputed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InfoIR:
    name: str | None = None
    version: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class CapabilityIR:
    id: str | None = None
    description: str | None = None
    inputs: dict | None = None
    inputs_summary: str = "any"  # target-neutral type description
    outputs: dict | None = None
    outputs_summary: str = "any"
    scope_boundaries: str | None = None
    examples: list[dict] = field(default_factory=list)


@dataclass
class ToolIR:
    id: str | None = None
    type: str | None = None
    description: str | None = None
    schema: dict | None = None
    side_effects: str | None = None
    rate_limit: dict | None = None
    # Direct link, resolved from auth.scopesPerTool[tool.id] -- no more
    # authRef indirection for later stages to chase down.
    auth_scopes: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    retry_policy: dict | None = None


@dataclass
class DataContractIR:
    source: str | None = None
    classification: str | None = None
    allowed_operations: list[str] = field(default_factory=list)
    retention: str | None = None
    fields: list[str] = field(default_factory=list)
    pii_present: bool = False


@dataclass
class ModelIR:
    provider: str | None = None
    model: str | None = None
    parameters: dict | None = None
    prompt_template_ref: str | None = None
    planning_strategy: str | None = None
    fallback_model: str | None = None


@dataclass
class MemoryIR:
    type: str = "none"
    scope: str | None = None
    ttl: str | None = None
    persistence_ref: str | None = None
    max_size_kb: int | None = None


@dataclass
class GuardrailsIR:
    content_policies: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    refusal_conditions: list[str] = field(default_factory=list)
    max_autonomy_steps: int | None = None
    pii_handling: str | None = None


@dataclass
class AuthIR:
    identity_ref: str | None = None
    credentials_ref: str | None = None
    scopes_per_tool: dict[str, list[str]] = field(default_factory=dict)
    token_lifetime_seconds: int = 3600


@dataclass
class HumanInLoopIR:
    checkpoints: list[str] = field(default_factory=list)
    escalation_path: str | None = None
    override_authority: str | None = None
    approval_timeout_behavior: str = "block"


@dataclass
class ObservabilityIR:
    logging: dict | None = None
    tracing: dict | None = None
    metrics: list[str] = field(default_factory=list)
    eval_suite_ref: str | None = None


@dataclass
class ErrorHandlingIR:
    on_tool_failure: str | None = None
    on_timeout: str | None = None
    on_low_confidence: str | None = None
    fallback_response: str | None = None
    confidence_threshold: float | None = None


@dataclass
class DeploymentIR:
    environments: list[str] = field(default_factory=list)
    rollout_strategy: str | None = None
    compatibility: str | None = None
    change_history_ref: str | None = None
    approval_required: bool | None = None


@dataclass
class AgentIR:
    """Root IR node. Everything a target adapter (Stage 4) needs, with no
    $refs, canonical enums, and derived fields precomputed."""

    spec_version: str | None = None
    info: InfoIR = field(default_factory=InfoIR)
    capabilities: list[CapabilityIR] = field(default_factory=list)
    tools: list[ToolIR] = field(default_factory=list)
    data_contracts: list[DataContractIR] = field(default_factory=list)
    model: ModelIR = field(default_factory=ModelIR)
    memory: MemoryIR | None = None
    guardrails: GuardrailsIR = field(default_factory=GuardrailsIR)
    auth: AuthIR = field(default_factory=AuthIR)
    human_in_loop: HumanInLoopIR | None = None
    observability: ObservabilityIR = field(default_factory=ObservabilityIR)
    error_handling: ErrorHandlingIR = field(default_factory=ErrorHandlingIR)
    deployment: DeploymentIR = field(default_factory=DeploymentIR)

    # Derived field (Section 7.3): true if the agent has any write/irreversible
    # tool, or a maxAutonomySteps ceiling that implies a checkpoint is needed
    # once that ceiling is reached. Computed once here so every target
    # adapter/template gets it for free instead of recomputing the logic.
    requires_human_approval: bool = False

    source_file: str = ""
