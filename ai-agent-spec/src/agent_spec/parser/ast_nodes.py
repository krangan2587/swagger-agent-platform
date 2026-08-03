"""
Typed AST nodes, one per schema section — per Section 7.1's design note:
"an InfoNode is a distinct type from a ToolNode, so later stages get
compile-time safety instead of ad hoc field lookups."

All fields default to None/empty. The Parser does NOT enforce required-field
completeness — that's the schema Validator's job (Stage 2a). A node built
here may be structurally incomplete; it will fail validation later, with a
proper schema error, rather than crash the Parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_spec.parser.location import SourceLocation


@dataclass
class InfoNode:
    name: str | None = None
    version: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: str | None = None
    tags: list[str] = field(default_factory=list)
    source_location: SourceLocation | None = None


@dataclass
class CapabilityNode:
    id: str | None = None
    description: str | None = None
    inputs: dict | None = None
    outputs: dict | None = None
    scope_boundaries: str | None = None
    examples: list[dict] = field(default_factory=list)
    source_location: SourceLocation | None = None


@dataclass
class ToolNode:
    id: str | None = None
    type: str | None = None
    description: str | None = None
    schema: dict | None = None
    side_effects: str | None = None
    rate_limit: dict | None = None
    auth_ref: str | None = None
    timeout_ms: int = 30000
    retry_policy: dict | None = None
    source_location: SourceLocation | None = None


@dataclass
class DataContractNode:
    source: str | None = None
    classification: str | None = None
    allowed_operations: list[str] = field(default_factory=list)
    retention: str | None = None
    fields: list[str] = field(default_factory=list)
    pii_present: bool = False
    source_location: SourceLocation | None = None


@dataclass
class ModelNode:
    provider: str | None = None
    model: str | None = None
    parameters: dict | None = None
    prompt_template_ref: str | None = None
    planning_strategy: str | None = None
    fallback_model: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class MemoryNode:
    type: str = "none"
    scope: str | None = None
    ttl: str | None = None
    persistence_ref: str | None = None
    max_size_kb: int | None = None
    source_location: SourceLocation | None = None


@dataclass
class GuardrailsNode:
    content_policies: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    refusal_conditions: list[str] = field(default_factory=list)
    max_autonomy_steps: int | None = None
    pii_handling: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class AuthNode:
    identity_ref: str | None = None
    credentials_ref: str | None = None
    scopes_per_tool: dict[str, list[str]] = field(default_factory=dict)
    token_lifetime_seconds: int = 3600
    source_location: SourceLocation | None = None


@dataclass
class HumanInLoopNode:
    checkpoints: list[str] = field(default_factory=list)
    escalation_path: str | None = None
    override_authority: str | None = None
    approval_timeout_behavior: str = "block"
    source_location: SourceLocation | None = None


@dataclass
class ObservabilityNode:
    logging: dict | None = None
    tracing: dict | None = None
    metrics: list[str] = field(default_factory=list)
    eval_suite_ref: str | None = None
    source_location: SourceLocation | None = None


@dataclass
class ErrorHandlingNode:
    on_tool_failure: str | None = None
    on_timeout: str | None = None
    on_low_confidence: str | None = None
    fallback_response: str | None = None
    confidence_threshold: float | None = None
    source_location: SourceLocation | None = None


@dataclass
class DeploymentNode:
    environments: list[str] = field(default_factory=list)
    rollout_strategy: str | None = None
    compatibility: str | None = None
    change_history_ref: str | None = None
    approval_required: bool | None = None
    source_location: SourceLocation | None = None


@dataclass
class AgentSpecAST:
    """Root AST node — mirrors the agentSpec root document."""

    spec_version: str | None = None
    info: InfoNode = field(default_factory=InfoNode)
    capabilities: list[CapabilityNode] = field(default_factory=list)
    tools: list[ToolNode] = field(default_factory=list)
    data_contracts: list[DataContractNode] = field(default_factory=list)
    model: ModelNode = field(default_factory=ModelNode)
    memory: MemoryNode | None = None
    guardrails: GuardrailsNode = field(default_factory=GuardrailsNode)
    auth: AuthNode = field(default_factory=AuthNode)
    human_in_loop: HumanInLoopNode | None = None
    observability: ObservabilityNode = field(default_factory=ObservabilityNode)
    error_handling: ErrorHandlingNode = field(default_factory=ErrorHandlingNode)
    deployment: DeploymentNode = field(default_factory=DeploymentNode)
    source_file: str = ""
