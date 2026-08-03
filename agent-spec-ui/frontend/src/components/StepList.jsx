const ICONS = {
  pending: "○",
  running: "◐",
  success: "✓",
  error: "✗",
};

export default function StepList({ steps }) {
  return (
    <ol className="step-list">
      {steps.map((step) => (
        <li key={step.id} className={`step step-${step.status}`}>
          <span className="step-icon">{ICONS[step.status]}</span>
          <div className="step-body">
            <span className="step-label">{step.label}</span>
            {step.detail && (
              <div className="step-detail">
                {Array.isArray(step.detail) ? (
                  <ul>
                    {step.detail.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                ) : (
                  <span>{step.detail}</span>
                )}
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
