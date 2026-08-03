export default function SpecEditor({
  value,
  onChange,
  examples,
  onLoadExample,
  outputFolder,
  onOutputFolderChange,
  target,
  targets,
  onTargetChange,
  disabled,
}) {
  function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => onChange(evt.target.result);
    reader.readAsText(file);
    e.target.value = ""; // allow re-uploading the same file later
  }

  return (
    <div className="spec-editor">
      <div className="toolbar">
        <label className="upload-button">
          Upload spec file
          <input
            type="file"
            accept=".yaml,.yml,.json"
            onChange={handleFileUpload}
            disabled={disabled}
            hidden
          />
        </label>

        <select
          onChange={(e) => e.target.value && onLoadExample(e.target.value)}
          defaultValue=""
          disabled={disabled}
        >
          <option value="" disabled>
            Load example spec...
          </option>
          {examples.map((ex) => (
            <option key={ex.id} value={ex.id}>
              {ex.label}
            </option>
          ))}
        </select>

        <select value={target} onChange={(e) => onTargetChange(e.target.value)} disabled={disabled}>
          {targets.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <input
          className="output-folder-input"
          type="text"
          value={outputFolder}
          onChange={(e) => onOutputFolderChange(e.target.value)}
          placeholder="output folder name"
          disabled={disabled}
        />
      </div>

      <textarea
        className="spec-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste or type your agent spec YAML here, or upload/load an example above..."
        spellCheck={false}
        disabled={disabled}
      />
    </div>
  );
}
