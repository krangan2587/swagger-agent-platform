"""
Local backend for the AI Agent Spec UI.

This does NOT reimplement or fake the pipeline -- it calls the real
agent_spec library (Parser, Schema+Policy Validator, IR Builder,
Template Engine, Output Packager) directly, and streams each stage's
real result to the browser over Server-Sent Events as it happens.

Run:
    uvicorn main:app --reload --port 8000

Requires `agent_spec` to be importable -- either because you've already
`pip install -e .`'d your ai-agent-spec checkout into this same venv
(recommended), or via the AGENT_SPEC_SRC env var / the relative-path
fallback below.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Make sure `agent_spec` is importable.
# ---------------------------------------------------------------------------
_env_src = os.environ.get("AGENT_SPEC_SRC")
if _env_src:
    sys.path.insert(0, _env_src)

try:
    import agent_spec  # noqa: F401
except ImportError:
    # Fallback: assume the standard sibling-folder layout used throughout
    # this project -- .../Swagger/agent-spec-ui/backend/main.py and
    # .../Swagger/ai-agent-spec/src sitting next to each other.
    _guess = Path(__file__).resolve().parents[2] / "ai-agent-spec" / "src"
    if _guess.exists():
        sys.path.insert(0, str(_guess))

from agent_spec.codegen import (  # noqa: E402
    TemplateEngine,
    TemplateRenderError,
    get_target_adapter,
    list_target_adapters,
)
from agent_spec.ir import build_ir  # noqa: E402
from agent_spec.packager import OutputPackager, OutputPackagerError  # noqa: E402
from agent_spec.parser import ParserError, parse_spec_file  # noqa: E402
from agent_spec.policy import validate_policy  # noqa: E402
from agent_spec.validator import validate_spec_file  # noqa: E402

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Agent Spec UI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_BASE = Path(os.environ.get("AGENT_SPEC_UI_OUTPUTS", "./generated-agents")).resolve()
OUTPUTS_BASE.mkdir(parents=True, exist_ok=True)

EXAMPLE_SPECS_DIR = Path(__file__).parent / "example_specs"

REGISTRY_PATH = OUTPUTS_BASE / ".agent-registry.json"


class GenerateRequest(BaseModel):
    specContent: str
    target: str = "python-service"
    outputFolder: str = "generated-agent"


# ---------------------------------------------------------------------------
# Simple metadata endpoints
# ---------------------------------------------------------------------------


@app.get("/api/targets")
def get_targets():
    return {"targets": list_target_adapters()}


@app.get("/api/example-specs")
def list_example_specs():
    specs = sorted(EXAMPLE_SPECS_DIR.glob("*.spec.yaml"))
    return {
        "specs": [
            {
                "id": p.name.removesuffix(".spec.yaml"),
                "filename": p.name,
                "label": p.name.removesuffix(".spec.yaml").replace("-", " "),
            }
            for p in specs
        ]
    }


@app.get("/api/example-specs/{spec_id}")
def get_example_spec(spec_id: str):
    match = EXAMPLE_SPECS_DIR / f"{spec_id}.spec.yaml"
    if not match.exists():
        raise HTTPException(status_code=404, detail=f"no example spec matching '{spec_id}'")
    return {"content": match.read_text(encoding="utf-8")}


# ---------------------------------------------------------------------------
# The real pipeline, streamed step by step
# ---------------------------------------------------------------------------


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _run_pipeline(spec_content: str, target: str, output_folder: str) -> Iterator[str]:
    run_id = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp(prefix="agent-spec-ui-"))
    spec_path = tmp_dir / "agent.spec.yaml"
    spec_path.write_text(spec_content, encoding="utf-8")

    def step(step_id: str, label: str):
        yield _sse({"step": step_id, "label": label, "status": "running"})

    try:
        # --- Step 1: schema validation (Stage 2a) ---------------------------
        yield from step("schema", "Validating schema")
        time.sleep(0.15)  # small pause so the UI can visibly show each stage
        schema_report = validate_spec_file(spec_path)
        if not schema_report.valid:
            yield _sse(
                {
                    "step": "schema",
                    "status": "error",
                    "detail": [str(e) for e in schema_report.errors],
                }
            )
            return
        yield _sse({"step": "schema", "status": "success", "detail": "Schema is valid."})

        # --- Step 2: parse into AST (Stage 1) -------------------------------
        yield from step("parse", "Parsing spec into AST")
        time.sleep(0.15)
        try:
            ast = parse_spec_file(spec_path)
        except ParserError as e:
            yield _sse({"step": "parse", "status": "error", "detail": [str(e)]})
            return
        yield _sse(
            {
                "step": "parse",
                "status": "success",
                "detail": f"Parsed {len(ast.capabilities)} capabilit(y/ies), {len(ast.tools)} tool(s).",
            }
        )

        # --- Step 3: policy validation (Stage 2b) ---------------------------
        yield from step("policy", "Validating business policy rules")
        time.sleep(0.15)
        policy_report = validate_policy(ast)
        if not policy_report.valid:
            yield _sse(
                {
                    "step": "policy",
                    "status": "error",
                    "detail": [str(e) for e in policy_report.errors],
                }
            )
            return
        yield _sse({"step": "policy", "status": "success", "detail": "All policy rules pass."})

        # --- Step 4: build IR (Stage 3) --------------------------------------
        yield from step("ir", "Building intermediate representation")
        time.sleep(0.15)
        ir = build_ir(ast)
        yield _sse(
            {
                "step": "ir",
                "status": "success",
                "detail": f"requiresHumanApproval = {ir.requires_human_approval}",
            }
        )

        # --- Step 5: generate code (Stage 4) ---------------------------------
        yield from step("codegen", f"Generating code for target '{target}'")
        time.sleep(0.15)
        try:
            adapter = get_target_adapter(target)
        except KeyError:
            yield _sse(
                {
                    "step": "codegen",
                    "status": "error",
                    "detail": [f"unknown target '{target}'"],
                }
            )
            return
        try:
            virtual_files = TemplateEngine(adapter).render(ir)
        except TemplateRenderError as e:
            yield _sse({"step": "codegen", "status": "error", "detail": [str(e)]})
            return
        yield _sse(
            {
                "step": "codegen",
                "status": "success",
                "detail": f"Rendered {len(virtual_files)} file(s).",
            }
        )

        # --- Step 6: package output (Stage 5) --------------------------------
        yield from step("package", "Packaging output project")
        time.sleep(0.15)
        OUTPUTS_BASE.mkdir(parents=True, exist_ok=True)  # in case it was deleted mid-session
        output_dir = OUTPUTS_BASE / output_folder
        try:
            report = OutputPackager().build(
                virtual_files=virtual_files,
                ir=ir,
                spec_path=spec_path,
                output_dir=output_dir,
                registry_path=REGISTRY_PATH,
            )
        except OutputPackagerError as e:
            yield _sse({"step": "package", "status": "error", "detail": [str(e)]})
            return
        yield _sse(
            {
                "step": "package",
                "status": "success",
                "detail": f"Wrote {len(report.files_written)} source file(s).",
            }
        )

        # --- Done -------------------------------------------------------------
        all_files = sorted(
            str(p.relative_to(output_dir)) for p in output_dir.rglob("*") if p.is_file()
        )
        yield _sse(
            {
                "step": "done",
                "status": "success",
                "outputDir": str(output_dir),
                "agentName": ir.info.name,
                "agentVersion": ir.info.version,
                "requiresHumanApproval": ir.requires_human_approval,
                "fileCount": len(all_files),
                "files": all_files,
                "downloadId": output_folder,
            }
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/generate")
def generate(req: GenerateRequest):
    safe_folder = "".join(c for c in req.outputFolder if c.isalnum() or c in "-_") or "generated-agent"
    return StreamingResponse(
        _run_pipeline(req.specContent, req.target, safe_folder),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# Download the generated project as a zip
# ---------------------------------------------------------------------------


@app.get("/api/download/{output_folder}")
def download(output_folder: str):
    safe_folder = "".join(c for c in output_folder if c.isalnum() or c in "-_")
    target_dir = OUTPUTS_BASE / safe_folder
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="output folder not found")

    zip_base = OUTPUTS_BASE / f"{safe_folder}-download"
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=target_dir)
    return FileResponse(zip_path, filename=f"{safe_folder}.zip", media_type="application/zip")
