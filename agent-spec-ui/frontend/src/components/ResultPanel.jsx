const API_BASE = "http://localhost:8000";

export default function ResultPanel({ result }) {
  if (!result) return null;

  return (
    <div className="result-panel">
      <h3>✅ Done</h3>
      <dl>
        <dt>Agent</dt>
        <dd>
          {result.agentName} <code>v{result.agentVersion}</code>
        </dd>
        <dt>Requires human approval</dt>
        <dd>{String(result.requiresHumanApproval)}</dd>
        <dt>Output directory</dt>
        <dd>
          <code>{result.outputDir}</code>
        </dd>
        <dt>Files generated</dt>
        <dd>{result.fileCount}</dd>
      </dl>

      <a
        className="download-button"
        href={`${API_BASE}/api/download/${result.downloadId}`}
        download
      >
        Download as .zip
      </a>

      <details>
        <summary>File list ({result.files.length})</summary>
        <ul className="file-list">
          {result.files.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
