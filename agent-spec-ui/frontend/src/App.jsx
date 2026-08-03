import { useEffect, useState } from "react";
import SpecEditor from "./components/SpecEditor.jsx";
import StepList from "./components/StepList.jsx";
import ResultPanel from "./components/ResultPanel.jsx";

const API_BASE = "http://localhost:8000";

const STEP_DEFINITIONS = [
  { id: "schema", label: "Validate schema" },
  { id: "parse", label: "Parse spec into AST" },
  { id: "policy", label: "Validate policy rules" },
  { id: "ir", label: "Build intermediate representation" },
  { id: "codegen", label: "Generate code" },
  { id: "package", label: "Package output project" },
];

function freshSteps() {
  return STEP_DEFINITIONS.map((s) => ({ ...s, status: "pending", detail: null }));
}

export default function App() {
  const [specContent, setSpecContent] = useState("");
  const [examples, setExamples] = useState([]);
  const [targets, setTargets] = useState(["python-service"]);
  const [target, setTarget] = useState("python-service");
  const [outputFolder, setOutputFolder] = useState("generated-agent");

  const [steps, setSteps] = useState(freshSteps());
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [fatalError, setFatalError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/example-specs`)
      .then((r) => r.json())
      .then((data) => setExamples(data.specs))
      .catch(() => {});
    fetch(`${API_BASE}/api/targets`)
      .then((r) => r.json())
      .then((data) => setTargets(data.targets))
      .catch(() => {});
  }, []);

  async function loadExample(id) {
    const res = await fetch(`${API_BASE}/api/example-specs/${id}`);
    const data = await res.json();
    setSpecContent(data.content);
    setResult(null);
    setSteps(freshSteps());
    setFatalError(null);
  }

  function applyEvent(event) {
    if (event.step === "done") {
      setResult(event);
      return;
    }
    setSteps((prev) =>
      prev.map((s) =>
        s.id === event.step
          ? { ...s, status: event.status, detail: event.detail ?? s.detail, label: event.label ?? s.label }
          : s
      )
    );
  }

  async function handleGenerate() {
    setIsRunning(true);
    setResult(null);
    setFatalError(null);
    setSteps(freshSteps());

    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ specContent, target, outputFolder }),
      });

      if (!response.ok || !response.body) {
        setFatalError(`Request failed: HTTP ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split("\n\n");
        buffer = messages.pop(); // last chunk may be incomplete -- keep it for next read

        for (const message of messages) {
          const line = message.trim();
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));
          applyEvent(event);
        }
      }
    } catch (err) {
      setFatalError(String(err));
    } finally {
      setIsRunning(false);
    }
  }

  const hasError = steps.some((s) => s.status === "error");

  return (
    <div className="app">
      <header>
        <h1>AI Agent Spec → Generated Agent</h1>
        <p className="subtitle">
          Edit or upload a spec, hit Generate, and watch it run through the real
          5-stage pipeline.
        </p>
      </header>

      <SpecEditor
        value={specContent}
        onChange={setSpecContent}
        examples={examples}
        onLoadExample={loadExample}
        outputFolder={outputFolder}
        onOutputFolderChange={setOutputFolder}
        target={target}
        targets={targets}
        onTargetChange={setTarget}
        disabled={isRunning}
      />

      <button
        className="generate-button"
        onClick={handleGenerate}
        disabled={isRunning || !specContent.trim()}
      >
        {isRunning ? "Generating..." : "Generate"}
      </button>

      {fatalError && <div className="fatal-error">{fatalError}</div>}

      {(isRunning || steps.some((s) => s.status !== "pending")) && (
        <StepList steps={steps} />
      )}

      {hasError && !isRunning && (
        <div className="failure-banner">
          Pipeline stopped — fix the issue above and try again.
        </div>
      )}

      <ResultPanel result={result} />
    </div>
  );
}
