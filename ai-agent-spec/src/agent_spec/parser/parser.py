"""
Stage 1 — Parser. Per Section 7.1:

Input:  a single spec file (.yaml/.yml/.json) plus any files it references via $ref
Output: a typed AST object graph, with every node's source location attached
Failure mode: parser-level errors (bad syntax, unresolved $ref, duplicate id)
              stop the pipeline immediately, with a file:line:column error.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from agent_spec.parser.ast_nodes import (
    AgentSpecAST,
    AuthNode,
    CapabilityNode,
    DataContractNode,
    DeploymentNode,
    ErrorHandlingNode,
    GuardrailsNode,
    HumanInLoopNode,
    InfoNode,
    MemoryNode,
    ModelNode,
    ObservabilityNode,
    ToolNode,
)
from agent_spec.parser.errors import ParserError
from agent_spec.parser.location import SourceLocation
from agent_spec.parser.refs import resolve_refs
from agent_spec.parser.yaml_loader import LocationMap, load_yaml_with_locations

_ID_BEARING_SECTIONS = ("capabilities", "tools")


class Parser:
    def parse(self, path: str | Path) -> AgentSpecAST:
        path = Path(path)
        if not path.exists():
            raise ParserError(f"spec file not found: {path}")

        raw, locations = self._load(path)
        resolved = resolve_refs(raw, root=raw, base_dir=path.parent, locations=locations)
        self._check_duplicate_ids(resolved, locations)
        return self._build_ast(resolved, locations, source_file=str(path))

    # ---- loading -----------------------------------------------------

    def _load(self, path: Path) -> tuple[dict, LocationMap]:
        text = path.read_text(encoding="utf-8")
        fmt = self._detect_format(path, text)

        if fmt == "yaml":
            try:
                data, locations = load_yaml_with_locations(text, str(path))
            except yaml.YAMLError as e:
                mark = getattr(e, "problem_mark", None)
                loc = (
                    SourceLocation(str(path), mark.line + 1, mark.column + 1)
                    if mark
                    else SourceLocation(str(path), 1, 1)
                )
                raise ParserError(f"malformed YAML: {e}", loc) from e
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                loc = SourceLocation(str(path), e.lineno, e.colno)
                raise ParserError(f"malformed JSON: {e.msg}", loc) from e
            locations = {}

        if not isinstance(data, dict):
            raise ParserError(
                f"expected a mapping at the document root, got {type(data).__name__}",
                locations.get(()),
            )
        return data, locations

    @staticmethod
    def _detect_format(path: Path, text: str) -> str:
        suffix = path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            return "yaml"
        if suffix == ".json":
            return "json"
        # Fallback: JSON is a syntactic subset of YAML, so trying JSON first
        # and falling back to YAML covers both without guessing wrong.
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            return "yaml"

    # ---- structural checks --------------------------------------------

    @staticmethod
    def _check_duplicate_ids(resolved: dict, locations: LocationMap) -> None:
        for section in _ID_BEARING_SECTIONS:
            items = resolved.get(section)
            if not isinstance(items, list):
                continue
            seen: dict[str, int] = {}
            for i, item in enumerate(items):
                if not isinstance(item, dict) or "id" not in item:
                    continue
                item_id = item["id"]
                if item_id in seen:
                    loc = locations.get((section, i, "id")) or locations.get((section, i))
                    raise ParserError(
                        f"duplicate id '{item_id}' in {section}[{i}] "
                        f"(first defined at {section}[{seen[item_id]}])",
                        loc,
                    )
                seen[item_id] = i

    # ---- AST construction ----------------------------------------------

    def _build_ast(self, d: dict, locations: LocationMap, source_file: str) -> AgentSpecAST:
        loc = lambda path: locations.get(path)  # noqa: E731

        return AgentSpecAST(
            spec_version=d.get("specVersion"),
            info=self._build_info(d.get("info", {}), locations, ("info",)),
            capabilities=[
                self._build_capability(item, locations, ("capabilities", i))
                for i, item in enumerate(d.get("capabilities", []) or [])
            ],
            tools=[
                self._build_tool(item, locations, ("tools", i))
                for i, item in enumerate(d.get("tools", []) or [])
            ],
            data_contracts=[
                self._build_data_contract(item, locations, ("dataContracts", i))
                for i, item in enumerate(d.get("dataContracts", []) or [])
            ],
            model=self._build_model(d.get("model", {}), locations, ("model",)),
            memory=(
                self._build_memory(d["memory"], locations, ("memory",))
                if "memory" in d
                else None
            ),
            guardrails=self._build_guardrails(d.get("guardrails", {}), locations, ("guardrails",)),
            auth=self._build_auth(d.get("auth", {}), locations, ("auth",)),
            human_in_loop=(
                self._build_human_in_loop(d["humanInLoop"], locations, ("humanInLoop",))
                if "humanInLoop" in d
                else None
            ),
            observability=self._build_observability(
                d.get("observability", {}), locations, ("observability",)
            ),
            error_handling=self._build_error_handling(
                d.get("errorHandling", {}), locations, ("errorHandling",)
            ),
            deployment=self._build_deployment(d.get("deployment", {}), locations, ("deployment",)),
            source_file=source_file,
        )

    @staticmethod
    def _build_info(d: dict, locations: LocationMap, path: tuple) -> InfoNode:
        return InfoNode(
            name=d.get("name"),
            version=d.get("version"),
            owner=d.get("owner"),
            description=d.get("description"),
            lifecycle=d.get("lifecycle"),
            tags=d.get("tags", []) or [],
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_capability(d: dict, locations: LocationMap, path: tuple) -> CapabilityNode:
        return CapabilityNode(
            id=d.get("id"),
            description=d.get("description"),
            inputs=d.get("inputs"),
            outputs=d.get("outputs"),
            scope_boundaries=d.get("scopeBoundaries"),
            examples=d.get("examples", []) or [],
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_tool(d: dict, locations: LocationMap, path: tuple) -> ToolNode:
        return ToolNode(
            id=d.get("id"),
            type=d.get("type"),
            description=d.get("description"),
            schema=d.get("schema"),
            side_effects=d.get("sideEffects"),
            rate_limit=d.get("rateLimit"),
            auth_ref=d.get("authRef"),
            timeout_ms=d.get("timeoutMs", 30000),
            retry_policy=d.get("retryPolicy"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_data_contract(d: dict, locations: LocationMap, path: tuple) -> DataContractNode:
        return DataContractNode(
            source=d.get("source"),
            classification=d.get("classification"),
            allowed_operations=d.get("allowedOperations", []) or [],
            retention=d.get("retention"),
            fields=d.get("fields", []) or [],
            pii_present=d.get("piiPresent", False),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_model(d: dict, locations: LocationMap, path: tuple) -> ModelNode:
        return ModelNode(
            provider=d.get("provider"),
            model=d.get("model"),
            parameters=d.get("parameters"),
            prompt_template_ref=d.get("promptTemplateRef"),
            planning_strategy=d.get("planningStrategy"),
            fallback_model=d.get("fallbackModel"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_memory(d: dict, locations: LocationMap, path: tuple) -> MemoryNode:
        return MemoryNode(
            type=d.get("type", "none"),
            scope=d.get("scope"),
            ttl=d.get("ttl"),
            persistence_ref=d.get("persistenceRef"),
            max_size_kb=d.get("maxSizeKb"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_guardrails(d: dict, locations: LocationMap, path: tuple) -> GuardrailsNode:
        return GuardrailsNode(
            content_policies=d.get("contentPolicies", []) or [],
            business_rules=d.get("businessRules", []) or [],
            refusal_conditions=d.get("refusalConditions", []) or [],
            max_autonomy_steps=d.get("maxAutonomySteps"),
            pii_handling=d.get("piiHandling"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_auth(d: dict, locations: LocationMap, path: tuple) -> AuthNode:
        return AuthNode(
            identity_ref=d.get("identityRef"),
            credentials_ref=d.get("credentialsRef"),
            scopes_per_tool=d.get("scopesPerTool", {}) or {},
            token_lifetime_seconds=d.get("tokenLifetimeSeconds", 3600),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_human_in_loop(d: dict, locations: LocationMap, path: tuple) -> HumanInLoopNode:
        return HumanInLoopNode(
            checkpoints=d.get("checkpoints", []) or [],
            escalation_path=d.get("escalationPath"),
            override_authority=d.get("overrideAuthority"),
            approval_timeout_behavior=d.get("approvalTimeoutBehavior", "block"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_observability(d: dict, locations: LocationMap, path: tuple) -> ObservabilityNode:
        return ObservabilityNode(
            logging=d.get("logging"),
            tracing=d.get("tracing"),
            metrics=d.get("metrics", []) or [],
            eval_suite_ref=d.get("evalSuiteRef"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_error_handling(d: dict, locations: LocationMap, path: tuple) -> ErrorHandlingNode:
        return ErrorHandlingNode(
            on_tool_failure=d.get("onToolFailure"),
            on_timeout=d.get("onTimeout"),
            on_low_confidence=d.get("onLowConfidence"),
            fallback_response=d.get("fallbackResponse"),
            confidence_threshold=d.get("confidenceThreshold"),
            source_location=locations.get(path),
        )

    @staticmethod
    def _build_deployment(d: dict, locations: LocationMap, path: tuple) -> DeploymentNode:
        return DeploymentNode(
            environments=d.get("environments", []) or [],
            rollout_strategy=d.get("rolloutStrategy"),
            compatibility=d.get("compatibility"),
            change_history_ref=d.get("changeHistoryRef"),
            approval_required=d.get("approvalRequired"),
            source_location=locations.get(path),
        )


def parse_spec_file(path: str | Path) -> AgentSpecAST:
    """Convenience function — the entry point later stages and the CLI call."""
    return Parser().parse(path)
