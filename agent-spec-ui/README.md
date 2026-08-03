# Agent Spec UI

A local web app for the `ai-agent-spec` pipeline: edit or upload a spec,
hit **Generate**, and watch it run through the real 5-stage pipeline
(schema validation → parse → policy validation → build IR → generate
code → package output) with live step-by-step progress.

This does **not** reimplement or fake the pipeline — the backend imports
and calls your actual `agent_spec` library directly. Every step you see
in the UI is a real call into the same code the `check-spec`/`build-agent`
CLI commands use.

## Prerequisites

- Your `ai-agent-spec` checkout, already set up with its own venv
  (`pip install -e ".[dev]"` run inside it at least once)
- Node.js 18+ and npm (for the frontend)

## 1. Backend setup

Use the **same venv** you already created for `ai-agent-spec` — it
already has `agent_spec` installed, so you just need to add a few more
packages to it.

```powershell
# from wherever your ai-agent-spec venv lives
..\ai-agent-spec\.venv\Scripts\activate

cd agent-spec-ui\backend
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Leave this running. You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

If `agent_spec` isn't importable for some reason (e.g. you're using a
different venv), set an environment variable pointing at its `src/`
folder before starting uvicorn:
```powershell
$env:AGENT_SPEC_SRC = "C:\path\to\ai-agent-spec\src"
uvicorn main:app --reload --port 8000
```

## 2. Frontend setup

In a **second terminal**:

```powershell
cd agent-spec-ui\frontend
npm install
npm run dev
```

Open the URL it prints — **http://localhost:5173**.

## 3. Using it

1. Either type/paste a spec into the editor, **upload** a `.yaml` file,
   or pick one of the 3 bundled example specs (easy/medium/hard) from
   the dropdown.
2. Set the output folder name (defaults to `generated-agent`) — this is
   the subfolder name under `backend/generated-agents/` the project gets
   written to. Reuse the same name across runs to test that hand-written
   code (`src/impl/`, `src/runtime/`, etc.) survives rebuilds, exactly
   like the CLI does.
3. Click **Generate**. You'll see each of the 6 steps go
   pending → running → success (or error, with the real validation/policy
   messages, if something's wrong with the spec).
4. On success, you get the agent's name/version, the
   `requiresHumanApproval` flag, a full file list, and a **Download as
   .zip** button.

Generated projects land in `backend/generated-agents/<output-folder>/` on
disk — you can also just open that folder directly in your editor instead
of downloading the zip.

## What's real vs. what's convenience

- **Real**: every pipeline stage, every validation error message, every
  generated file, the `src/impl/` preservation behavior on rebuild.
- **Convenience-only**: the backend writes your pasted/uploaded spec
  content to a temp file as `agent.spec.yaml` before handing it to the
  pipeline (the pipeline needs a real file path, per its existing
  contract) — this doesn't change any pipeline behavior, it's just how
  the browser's text gets to disk.

## Project layout

```
agent-spec-ui/
├── backend/
│   ├── main.py              # FastAPI app wrapping agent_spec, SSE streaming
│   ├── requirements.txt
│   └── example_specs/       # the 3 easy/medium/hard specs, served to the UI
└── frontend/
    ├── src/
    │   ├── App.jsx            # main app: state, SSE consumption via fetch
    │   ├── App.css
    │   └── components/
    │       ├── SpecEditor.jsx  # textarea + upload + example picker
    │       ├── StepList.jsx    # live progress list
    │       └── ResultPanel.jsx # done state + download button
    ├── package.json
    └── vite.config.js
```
