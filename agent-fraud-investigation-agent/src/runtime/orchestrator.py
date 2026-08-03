"""
Agent orchestrator -- the layer the spec-to-code generator does NOT
produce, because the spec (v0.1) has no "triggers"/"ingress" section. It
declares capabilities and tools, but not what invokes the agent (an HTTP
request? a Kafka message? a cron job?) or how a single incoming request
picks a capability, calls it, and enforces guardrails around the result.

This is genuinely new engineering, hand-written once per agent. What the
generator gives you to build it on top of:
  - src/handlers/<capability>.py  -- one entry point per capability
  - src/guardrails/policy_hooks.py -- REQUIRES_HUMAN_APPROVAL, checks
  - the IR's humanInLoop section (checkpoints, escalation path)

This orchestrator is intentionally simple (dispatch + one guardrail gate)
-- a `react` or `plan-execute` planningStrategy would add a loop here that
calls the model to decide the next tool call, rather than dispatching
straight to one handler per request.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from src.guardrails import policy_hooks


@dataclass
class PendingApproval:
    """Returned instead of a result when a capability's output requires a
    human checkpoint before anything downstream acts on it."""

    capability_id: str
    result: dict
    escalation_path: str


class AgentOrchestrator:
    def __init__(self, capability_ids: list[str]):
        self._capability_ids = capability_ids

    def _load_handler(self, capability_id: str):
        module_name = capability_id.replace("-", "_")
        module = importlib.import_module(f"src.handlers.{module_name}")
        return module

    def handle_request(self, capability_id: str, input_data: dict[str, Any]):
        if capability_id not in self._capability_ids:
            raise ValueError(f"unknown capability: {capability_id!r}")

        # 1. Guardrail check BEFORE calling the model/tools at all.
        refusal = policy_hooks.check_refusal(input_data)
        if refusal:
            return {"refused": True, "reason": refusal}

        # 2. Run the capability (which internally calls whatever tools it needs).
        handler = self._load_handler(capability_id)
        result = handler.handle(input_data)

        # 3. If this agent's guardrails require human approval before a
        #    write/irreversible action lands, don't let the result "count"
        #    yet -- hand it to the escalation path instead of returning it
        #    as final.
        if policy_hooks.REQUIRES_HUMAN_APPROVAL and self._result_needs_checkpoint(result):
            return PendingApproval(
                capability_id=capability_id,
                result=result,
                escalation_path="team:fraud-senior-investigators",
            )

        return result

    @staticmethod
    def _result_needs_checkpoint(result: dict) -> bool:
        """Real logic would inspect which capability/tool produced this
        result and match it against humanInLoop.checkpoints from the spec
        (e.g. "before_case_record_created"). Simplified here to: anything
        that looks like it proposes an action needs a human to confirm it."""
        return isinstance(result, dict) and result.get("proposesAction", False)
