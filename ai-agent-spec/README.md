# AI Agent Specification — Implementation

Python implementation of the AI Agent Specification schema and code
generator, built step by step per the Build Plan (Section 10 of the
reference doc).

**Status: all 5 pipeline stages complete and tested end to end (62/62
tests passing).** See `enterprise-test-specs/` for three realistic,
verified example specs (easy/medium/hard) proving `spec → validated →
generated agent project` works end to end.

## Status: Step 6 of 8 — Output Packager (Stage 5). Full pipeline complete.

Currently implemented — all five pipeline stages, end to end:
- The formal JSON Schema (Appendix A) — `src/agent_spec/schema/agent_spec_schema.json`
- Schema validation logic + `validate-spec` CLI — `src/agent_spec/validator.py`, `cli.py`
- Parser (Stage 1) — `src/agent_spec/parser/`, `inspect-spec` CLI
- Policy Validator (Stage 2b) — `src/agent_spec/policy/`
- `pipeline.py` + `check-spec` CLI — the combined Stage 2 gate
- IR Builder (Stage 3) — `src/agent_spec/ir/`, `build-ir` CLI
- Template Engine + Python target adapter (Stage 4) — `src/agent_spec/codegen/`, `generate-code` CLI
- **Output Packager (Stage 5)** — `src/agent_spec/packager/`:
  - `docs_renderer.py` — data-driven `docs/reference.html` generator (deliberately
    *not* a template, per Section 7.5 step 2 — built directly from the IR in Python)
  - `registry_store.py` + `changelog.py` — a local JSON stand-in for the Agent
    Registry, used to diff `info.version` and render `CHANGELOG.md`
  - `packaging_templates/` — small fixed Jinja templates for `deploy/Dockerfile`,
    `deploy/manifest.yaml`, and `tests/{unit,contract,eval}/` stubs
  - `packager.py` — `OutputPackager.build()`: writes everything atomically
    (temp dir → move into place only on full success), plus a final
    consistency check against Stage 4's virtual file set
- **`build-agent` CLI** — runs the complete 5-stage pipeline: spec file in,
  full runnable project on disk out
- Tests covering project structure, changelog versioning (including
  idempotent re-generation and version bumps), and atomicity on
  failure — `tests/test_packager.py`

Not yet built: CI wiring (Step 7), a real pilot run (Step 8).

### The complete generated project

Running `build-agent examples/kyc-refresh-agent.spec.yaml` produces exactly
the tree Section 8.1 describes:

```
agent-kyc-refresh-agent/
  spec/kyc-refresh-agent.spec.yaml   # copy of the source spec
  src/
    tools/get_customer_profile.py
    tools/update_kyc_record.py
    handlers/summarize_kyc_gaps.py
    handlers/draft_outreach_note.py
    guardrails/policy_hooks.py
    prompts/kyc_refresh.py
    memory/session_store.py
  tests/
    unit/test_get_customer_profile.py, test_update_kyc_record.py
    contract/test_get_customer_profile_contract.py, ...
    eval/test_eval_suite.py
  docs/
    reference.html                   # live-rendered from the IR
  deploy/
    Dockerfile
    manifest.yaml
  CHANGELOG.md
```

Verified this is real, working output — not just files that exist:
- The generated `.py` files import cleanly and their stubs raise
  `NotImplementedError` as designed.
- The generated `tests/` collect and run under real `pytest` (5 tests,
  all correctly `SKIPPED` pending real wiring, not silently passing).
- Building the same spec twice doesn't duplicate the CHANGELOG entry;
  bumping `info.version` and rebuilding adds a new one, newest-first.
- A build that fails partway (e.g. spec file missing at copy time) leaves
  a pre-existing output directory completely untouched — proven with a
  planted marker file that survives the failed build.

### Where two genuine test-writing mistakes were caught and fixed

While building this out, two of *my own test assertions* were wrong (not
the implementation) — caught by actually running the tests rather than
assuming they'd pass:
1. Assumed `kyc-refresh-agent.spec.yaml` had no `memory` section; it does
   (Section 5 of the reference doc declares one). Fixed the test to use
   the right fixture instead of changing the code.
2. Asserted a literal substring that ignored an HTML tag boundary
   (`Human approval required:</strong> True`, not `...required: True`).
   Fixed the assertion, not the renderer.

## Setup

```bash
# from the project root
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick start — prove it works in 3 commands

```bash
pytest -v                                                    # 62/62 tests pass
check-spec enterprise-test-specs/03-hard-fraud-investigation-agent.spec.yaml
build-agent enterprise-test-specs/03-hard-fraud-investigation-agent.spec.yaml
# -> agent-fraud-investigation-agent/ with 11 src files, tests, docs, deploy manifests
```

See `enterprise-test-specs/README.md` for the easy/medium/hard specs and
exactly what each one proves about the pipeline.

## Filling in real capability logic without losing it on rebuild

Generated files (`src/tools/*.py`, `src/handlers/*.py`, `src/guardrails/`,
`src/prompts/`, `src/memory/`) are pure wiring — each one just delegates
to a same-named module under `src/impl/`:

```python
# src/tools/create_case_record.py -- GENERATED, regenerated every build
from src.impl.tools import create_case_record as _impl
def call(**kwargs):
    return _impl.call(**kwargs)
```

`src/impl/tools/*.py` and `src/impl/handlers/*.py` are scaffolded once
(with a `NotImplementedError` stub) and **never touched again** by the
generator. Put your real database/MCP/HTTP client code there.

**The general rule, not just for `impl/`:** any directory under `src/`
that isn't one of the generator's own five (`tools/`, `handlers/`,
`guardrails/`, `prompts/`, `memory/`) is preserved automatically across
rebuilds — so a hand-built orchestrator at `src/runtime/`, a mock service
at `src/mock_services/`, or any other custom directory survives too. This
is implemented once in `OutputPackager._preserve_hand_written_impl()` and
covered by `tests/test_packager.py` (including a test that actually
imports and calls the generated shim in a subprocess to prove the
delegation really works at runtime, not just via string matching).

**Anywhere else in the project is not protected** — a top-level directory
(sitting next to `src/`, `tests/`, `deploy/`) gets wiped on every rebuild,
since the packager treats the whole output directory as disposable except
for what's inside `src/`.

## Usage

```bash
# validate the known-good example
validate-spec examples/kyc-refresh-agent.spec.yaml

# validate the known-broken example (should print 3 errors)
validate-spec examples/invalid-example.spec.yaml

# your own spec
validate-spec path/to/your-agent.spec.yaml
```

Exit code is `0` if valid, `1` if schema-invalid, `2` if the file couldn't
be read/parsed at all.

```bash
# parse a spec and dump its typed AST as JSON (resolved $refs, source locations)
inspect-spec examples/kyc-with-refs.spec.yaml

# see a located parser error (duplicate tool id)
inspect-spec examples/duplicate-id.spec.yaml

# see a located parser error (malformed YAML)
inspect-spec examples/malformed.spec.yaml
```

```bash
# full Stage 2 gate: schema validation + policy validation together
check-spec examples/kyc-refresh-agent.spec.yaml          # passes both

check-spec examples/policy-violation-checkpoints.spec.yaml   # schema-valid, policy-invalid
check-spec examples/policy-violation-pii.spec.yaml
check-spec examples/policy-violation-restricted-provider.spec.yaml
check-spec examples/policy-violation-production-approval.spec.yaml

check-spec examples/invalid-example.spec.yaml             # fails BOTH schema and policy
check-spec examples/duplicate-id.spec.yaml                 # can't parse -> policy can't run
```

```bash
# Stage 3: build the IR (only for specs that pass Stage 2)
build-ir examples/kyc-refresh-agent.spec.yaml               # writes kyc-refresh-agent.ir.json
build-ir examples/kyc-with-refs.spec.yaml --stdout           # print instead of writing

# refuses to build IR for a Stage-2-invalid spec
build-ir examples/policy-violation-checkpoints.spec.yaml
```

```bash
# Stage 4: run the Template Engine + Python target adapter
generate-code examples/kyc-refresh-agent.spec.yaml            # lists the 7 generated files

# write them to disk to actually inspect them (preview only -- see the
# module docstring in generate_cli.py; the real Output Packager is Step 6)
generate-code examples/kyc-refresh-agent.spec.yaml --out /tmp/gen-preview
cat /tmp/gen-preview/src/guardrails/policy_hooks.py

# also gates on Stage 2
generate-code examples/policy-violation-checkpoints.spec.yaml
```

```bash
# Stage 5 / full pipeline: build a complete, runnable agent project
build-agent examples/kyc-refresh-agent.spec.yaml
# -> writes agent-kyc-refresh-agent/ with src/, tests/, docs/, deploy/, CHANGELOG.md

# custom output dir + registry
build-agent examples/kyc-refresh-agent.spec.yaml --out my-agent/ --registry my-registry.json

# rebuild the same spec: CHANGELOG.md entry is NOT duplicated
build-agent examples/kyc-refresh-agent.spec.yaml

# bump info.version in the YAML, rebuild: a new CHANGELOG.md entry appears
# (newest first), and the local registry file records the new version too

# run the generated tests (they collect and SKIP cleanly, pending real wiring)
cd agent-kyc-refresh-agent && python -m pytest tests/ -v
```

## Tests

```bash
pytest -v
```

## VSCode

1. Open this folder in VSCode (`code .`).
2. Select the `.venv` interpreter: `Cmd/Ctrl+Shift+P` → *Python: Select
   Interpreter* → `.venv/bin/python`.
3. Install the recommended extensions if prompted (Python, Pylance, Ruff).
4. Run/debug via the **Run and Debug** panel — two launch configs are
   preconfigured (valid spec / invalid spec).
5. Run tests via the **Testing** panel (flask icon) — pytest is
   preconfigured to discover `tests/`.

## Project layout

```
ai-agent-spec/
├── src/agent_spec/
│   ├── schema/agent_spec_schema.json   # Appendix A JSON Schema
│   ├── validator.py                    # Stage 2a: schema validation
│   └── cli.py                          # validate-spec command
├── examples/                           # spec fixtures used by tests + CLI
├── tests/
├── pyproject.toml
└── .vscode/                            # settings + debug configs
```
