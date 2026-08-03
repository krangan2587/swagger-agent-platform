# Enterprise Test Specs — Easy / Medium / Hard

Three realistic, complete agent specs for proving the `spec → validated →
generated agent code` pipeline end to end, at increasing complexity. All
three are schema-valid AND policy-compliant — verified against the actual
codebase, not hand-checked.

## The three specs

| | Spec | Capabilities | Tools | Data | Memory | Lifecycle |
|---|---|---|---|---|---|---|
| **Easy** | `01-easy-it-kb-assistant.spec.yaml` | 1 | 1 (read) | internal, no PII | none | pilot |
| **Medium** | `02-medium-expense-triage-agent.spec.yaml` | 2 | 2 (1 read, 1 write) | confidential, PII | session | pilot |
| **Hard** | `03-hard-fraud-investigation-agent.spec.yaml` | 4 | 4 (read/write/irreversible, mcp+http) | 3 sources incl. restricted | long-term | **production** |

### Easy — IT Knowledge Base Assistant
A read-only Q&A agent. Proves the minimal-but-complete case: no PII, no
write tools, no autonomy ceiling — so `humanInLoop` is entirely absent
(it's optional at the schema level) and the generated
`REQUIRES_HUMAN_APPROVAL` comes out `False`.

### Medium — HR Expense Report Triage Agent
Adds a write-side-effect tool and a PII-bearing data contract, which
trips two of the five policy rules — so `humanInLoop.checkpoints` and
`guardrails.piiHandling` are both required *and present*. Also exercises
`session` memory, a `retryPolicy` + `rateLimit` on one tool, and per-tool
auth scope resolution across two different tools.

### Hard — Fraud Investigation & Case Management Agent
Production-lifecycle banking agent. Exercises the full schema surface:
- `sideEffects: irreversible` (the highest-risk tool category)
- `classification: restricted` data → requires an approved `model.provider`
- `lifecycle: production` → requires `deployment.approvalRequired: true`
- `memory.type: long-term` with `persistenceRef` + `maxSizeKb`
- `model.fallbackModel`, `plan-execute` strategy, `confidenceThreshold`
- Both `mcp` and `http` tool types in the same agent
- Multiple `dataContracts` with different classifications and retentions
- Full `observability`, and every `errorHandling` enum value exercised

## How to run these

From inside the `ai-agent-spec` project (see the main README for setup):

```bash
# Stage 2: schema + policy validation
check-spec 01-easy-it-kb-assistant.spec.yaml
check-spec 02-medium-expense-triage-agent.spec.yaml
check-spec 03-hard-fraud-investigation-agent.spec.yaml
# all three should print: ✅ Spec passes schema validation and all policy rules.

# Full pipeline: spec -> real, runnable Python agent project
build-agent 01-easy-it-kb-assistant.spec.yaml
build-agent 02-medium-expense-triage-agent.spec.yaml
build-agent 03-hard-fraud-investigation-agent.spec.yaml

# confirm the generated tests actually collect and run
cd agent-it-kb-assistant && python -m pytest tests/ -v && cd ..
cd agent-expense-report-triage-agent && python -m pytest tests/ -v && cd ..
cd agent-fraud-investigation-agent && python -m pytest tests/ -v && cd ..
```

## What was actually verified before delivery

Running these through the real codebase (not just written by hand and
assumed correct) caught one genuine bug: the hard spec originally had
`humanInLoop.approvalTimeoutBehavior: escalate`, which isn't a valid enum
value (only `block` / `proceed-with-log` / `abort` are). The schema
validator caught it immediately; it's fixed in the version here.

Confirmed for all three:
- `check-spec` passes cleanly (schema + all 5 policy rules)
- `build-agent` produces a complete project (4 / 7 / 11 generated `src/`
  files respectively, escalating with complexity)
- The generated `docs/reference.html`, `CHANGELOG.md`, `deploy/Dockerfile`,
  and `deploy/manifest.yaml` are all populated correctly from each spec
- The generated `tests/` directories (3 / 5 / 9 files) collect and run
  cleanly under real `pytest` — all `SKIPPED` as designed (stubs awaiting
  real endpoint wiring), not silently passing or erroring
- `REQUIRES_HUMAN_APPROVAL` in the generated guardrail hooks is `False`
  for the easy spec and `True` for medium/hard, exactly as each spec's
  tools and guardrails should derive
- The hard spec's `long-term` memory correctly produces a
  `PERSISTENCE_REF` in the generated memory store, which the easy/medium
  specs (session or no memory) don't have
