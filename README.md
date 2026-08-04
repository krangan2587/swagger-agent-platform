# AI Agent Spec — Complete Setup & Operations Guide

This covers **two separate codebases** that work together:

| | What it is | Where |
|---|---|---|
| **`ai-agent-spec`** | The generator — a Python CLI tool that turns a YAML agent spec into a validated, runnable Python project | `ai-agent-spec/` |
| **`agent-spec-ui`** | A local web UI (FastAPI + React) wrapping the generator, so you can edit a spec and watch it build in a browser | `agent-spec-ui/` |

You can use `ai-agent-spec` entirely on its own from the command line. `agent-spec-ui` requires `ai-agent-spec` to already be installed — it doesn't duplicate any pipeline logic, it just calls into it.

---

## 1. Prerequisites

- Python 3.10+
- Node.js 18+ and npm (only needed for `agent-spec-ui`'s frontend)
- Both projects unzipped as **sibling folders** in the same parent directory, e.g.:
  ```
  Swagger\
  ├── ai-agent-spec\
  └── agent-spec-ui\
  ```

---

## 2. `ai-agent-spec` — the generator

### 2.1 Setup

```powershell
cd ai-agent-spec
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### 2.2 Confirm it works

```powershell
pytest -v
# expect: 62 passed
```

### 2.3 All CLI commands

Six commands, each one exposing a different stage (or combination of stages) of the pipeline. All take a spec file path as their first argument.

| Command | Pipeline stage(s) | What it does |
|---|---|---|
| `validate-spec <spec.yaml>` | 2a (schema) | Checks the spec against the JSON Schema only. Exit 0/1/2. |
| `inspect-spec <spec.yaml>` | 1 (parse) | Parses the spec into an AST and dumps it as JSON — resolves `$ref`s, shows source locations. |
| `check-spec <spec.yaml>` | 2a + 2b (schema + policy) | Full validation gate: schema AND the 5 business-policy rules. This is what `build-agent` runs before doing anything else. |
| `build-ir <spec.yaml> [--stdout] [-o file]` | 1–3 | Builds the normalized Intermediate Representation. Refuses to run if Stage 2 fails. |
| `generate-code <spec.yaml> [--target python-service] [--out DIR]` | 1–4 | Renders the IR through the target adapter's templates. `--out` previews the raw generated files only (no docs/tests/deploy — that's Stage 5). |
| `build-agent <spec.yaml> [--out DIR] [--registry FILE]` | 1–5, full pipeline | **The one you'll use most.** Produces a complete, runnable project: `src/`, `tests/`, `docs/`, `deploy/`, `CHANGELOG.md`. |

### 2.4 Typical usage

```powershell
# validate only
check-spec enterprise-test-specs\03-hard-fraud-investigation-agent.spec.yaml

# full build
build-agent enterprise-test-specs\03-hard-fraud-investigation-agent.spec.yaml --out ..\my-agent
```

### 2.5 The three bundled example specs

`enterprise-test-specs\` has three ready-to-run specs at increasing complexity:

- `01-easy-it-kb-assistant.spec.yaml` — read-only, no PII, no write tools
- `02-medium-expense-triage-agent.spec.yaml` — one write tool (triggers a checkpoint requirement), PII data, session memory
- `03-hard-fraud-investigation-agent.spec.yaml` — production lifecycle, restricted data, long-term memory, mixed MCP/HTTP tools

---

## 3. `agent-spec-ui` — the web UI

### 3.1 Backend setup

Reuses the **same venv** you already made for `ai-agent-spec` — it already has `agent_spec` installed, you're just adding a few more packages to it.

```powershell
cd ai-agent-spec
.venv\Scripts\activate

cd ..\agent-spec-ui\backend
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Leave this running. If `agent_spec` somehow isn't importable (different venv, unusual layout), set:
```powershell
$env:AGENT_SPEC_SRC = "C:\path\to\ai-agent-spec\src"
```
before starting uvicorn.

### 3.2 Frontend setup (separate terminal)

```powershell
cd agent-spec-ui\frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

### 3.3 Using it

1. Type/paste a spec, upload a `.yaml` file, or pick one of the 3 bundled examples.
2. Set an output folder name.
3. Click **Generate** — watch 6 live steps (schema → parse → policy → IR → codegen → package).
4. On success: agent name/version, `requiresHumanApproval`, file list, **Download as .zip**.
5. Generated projects land in `agent-spec-ui\backend\generated-agents\<folder-name>\` on disk.

Rebuilding into the **same folder name** preserves any hand-written code you've added under `src/impl/`, `src/runtime/`, or any other custom folder under `src/` — this was specifically tested through the UI's own API, not just assumed from the CLI.

---

## 4. What this system actually does

A spec (`.yaml`) goes through 5 stages, each independently testable:

```
Parser (Stage 1)     -- YAML/JSON -> typed AST, resolves $ref, source locations
Validator (Stage 2)  -- schema check (2a) + 5 business-policy rules (2b)
IR Builder (Stage 3) -- normalizes AST -> IR: canonical enums, resolved auth
                         scopes, derived fields like requiresHumanApproval
Template Engine       -- IR -> in-memory virtual files (one target adapter:
(Stage 4)                python-service, using Jinja2 templates)
Output Packager       -- writes everything to disk: src/, tests/, docs/,
(Stage 5)                deploy/, CHANGELOG.md -- atomically, preserving
                         any hand-written code under src/
```

Every generated tool binding (`src/tools/*.py`) and capability handler (`src/handlers/*.py`) is a thin shim that delegates to `src/impl/`, which is scaffolded once and never overwritten. That's the mechanism that lets you add real business logic (database calls, MCP clients, HTTP calls) without it being destroyed on the next regeneration.

---

## 5. What this system does NOT do — read this before you assume something works

### 5.1 It generates *contracts*, not *behavior*

Every `src/tools/*.py` and `src/handlers/*.py` file, out of the box, just `raise NotImplementedError`. The generator has no idea what a database, an MCP server, or Kafka is. **All real behavior is something you write by hand** in `src/impl/` (and any other custom folder you add under `src/`). This isn't a bug to fix — it's the design: the spec is a declarative contract, not a program.

### 5.2 The spec has no concept of "what triggers the agent"

There is no `triggers:` or `ingress:` section in the schema. The generator never produces anything like an HTTP server, a Kafka consumer, or a cron job. If you need one, you build it by hand (we did this earlier as `src/runtime/orchestrator.py` + `src/runtime/kafka_trigger.py`) — it's your own code, in a custom folder, protected by the same preservation mechanism as `src/impl/`.

### 5.3 `deploy/Dockerfile` is scaffolding, not a working container build

The generated Dockerfile has two concrete gaps, by design (it can't know either of these things):

```dockerfile
# TODO: add a requirements.txt / pyproject.toml install step once the
# generated tool bindings have real dependencies.
...
CMD ["python", "-m", "src.handlers"]
```

- **No dependency installation step.** The moment you add `mcp`, `sqlalchemy`, `kafka-python`, etc. to `src/impl/`, you need to maintain your own `requirements.txt` and add a `RUN pip install -r requirements.txt` line yourself.
- **The `CMD` doesn't point at a real entrypoint.** `src.handlers` is a package of individual functions, not something runnable. You need to change `CMD` to whatever your actual entrypoint is (e.g. `python -m src.runtime.kafka_trigger`) once you've built one.

`deploy/manifest.yaml` has the same character: correct skeleton, populated from `deployment.*` in the spec, but not a complete, review-ready Kubernetes manifest.

### 5.4 Only one target adapter exists: `python-service`

The `TargetAdapter` interface (Section 7.6-style plugin design) supports adding more targets (e.g. TypeScript), but only Python is actually implemented. `--target` accepts nothing else right now.

### 5.5 The CHANGELOG/registry is a local stand-in, not a real registry service

`.agent-registry.json` is a flat JSON file the packager reads/writes locally to diff versions for `CHANGELOG.md`. It is **not** a real, centrally-managed Agent Registry — there's no multi-user concurrency handling, no access control, nothing beyond "a JSON file on disk that happens to track version history."

### 5.6 The rebuild-preservation mechanism has one hard boundary

Anything under `src/` that isn't `tools/`, `handlers/`, `guardrails/`, `prompts/`, or `memory/` survives a rebuild automatically. **Anything outside `src/` (top-level files/folders next to `src/`, `tests/`, `deploy/`) does not** — it gets wiped on every rebuild along with the rest of the disposable output. If you build a helper script or service that needs to persist, it has to live under `src/`.

### 5.7 CI/CD wiring was never built

The original 8-step plan included "Step 7: CI wiring" (e.g. a GitHub Actions workflow running `check-spec` as a required PR check) and "Step 8: a real pilot run." Neither was built. `check-spec`/`build-agent` are ready to be called from a CI pipeline, but no pipeline configuration exists yet.

### 5.8 The web UI is a local single-user dev tool, not a deployable service

No authentication, no multi-user isolation, no production hardening. It's meant to run on `localhost` for one developer at a time. Don't expose it on a network.

### 5.9 The MCP/SQLite integration built earlier in this project is a worked example, not a template

`src/impl/tools/create_case_record.py` (real MCP + SQLite) and `src/mock_services/transaction_history_server.py` (a fake MCP server) exist only in the specific worked-example project we built by hand. The generator does not produce anything like this automatically for a new spec — you'd write equivalent code yourself for each new tool that needs a real backend.

### 5.10 UI testing was done via HTTP client, not a real browser

Backend endpoints and the full SSE-streamed pipeline (including the failure path and the rebuild-preservation behavior) were verified with a real Python HTTP client hitting the real server — genuine end-to-end proof at the API layer. The React frontend's build was verified (`npm run build`, zero errors) and the dev server confirmed to serve correctly, but no automated browser test (Playwright/Selenium) clicked through the actual UI. Manual testing in your own browser is how that gap gets closed.

---

## 6. Known pitfall: pointing `--out` at an empty folder looks like "everything got wiped"

If you run `build-agent ... --out <path>` against a location that has never been built into before, you'll get a fresh, stub-only project — correctly. This can *look* like your hand-written code got deleted if you expected it to already be there but it was actually never copied to that exact path. Before assuming a preservation bug, check: does `src/impl/tools/<name>.py` contain `NotImplementedError` (fresh stub) or your real code? If it's a fresh stub, nothing was wiped — nothing was there yet.

---

## 7. Quick command reference

```powershell
# --- ai-agent-spec ---
cd ai-agent-spec
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -v
check-spec <spec.yaml>
build-agent <spec.yaml> --out <output-dir>

# --- agent-spec-ui backend (same venv as above) ---
cd ..\agent-spec-ui\backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# --- agent-spec-ui frontend (new terminal) ---
cd agent-spec-ui\frontend
npm install
npm run dev
# open http://localhost:5173
```
