"""
Real Kafka consumer wiring for production use. Requires `pip install
kafka-python` and a live broker -- neither is available in this sandbox,
so this file is reference code, not something we ran.

Kafka is architecturally different from an MCP/HTTP tool: a tool is
something the agent CALLS OUT to; Kafka here is something that CALLS THE
AGENT -- an ingress/trigger, not a capability. That's why it lives in
src/runtime/ alongside the orchestrator, not in src/tools/.
"""

from __future__ import annotations

import json

from kafka import KafkaConsumer

from src.runtime.orchestrator import AgentOrchestrator

TOPIC = "fraud-alerts"
BOOTSTRAP_SERVERS = ["kafka.internal:9092"]


def run_consumer_loop() -> None:
    orchestrator = AgentOrchestrator(
        capability_ids=[
            "summarize-alert",
            "gather-evidence",
            "draft-case-narrative",
            "recommend-disposition",
        ]
    )

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id="fraud-investigation-agent",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,  # commit only after successful handling
    )

    for message in consumer:
        alert_event = message.value  # e.g. {"alertId": "ALRT-9001"}
        try:
            result = orchestrator.handle_request("summarize-alert", alert_event)
            # TODO: publish `result` onward (another topic, a case system, etc.)
            consumer.commit()
        except Exception:
            # TODO: route to a dead-letter topic instead of silently dropping.
            raise


if __name__ == "__main__":
    run_consumer_loop()
