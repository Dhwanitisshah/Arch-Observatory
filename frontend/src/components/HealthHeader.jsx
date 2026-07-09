import { SMELL_ICONS, SMELL_LABELS, SMELL_TYPES } from "../lib/smellUtils";

function scoreColor(score) {
  if (score >= 80) return "#22c55e";
  if (score >= 50) return "#eab308";
  return "#ef4444";
}

export default function HealthHeader({ run, repoUrl }) {
  const score = run.health_score ?? 0;

  return (
    <div className="health-header">
      <div className="health-score" style={{ color: scoreColor(score) }}>
        {Math.round(score)}
      </div>
      <div className="health-meta">
        <div className="repo-name">{repoUrl}</div>
        <div className="repo-sub">{run.py_file_count} Python files analyzed</div>
      </div>
      <div className="chip-row">
        {SMELL_TYPES.map((type) => (
          <div key={type} className="chip">
            <span className="type-icon">{SMELL_ICONS[type]}</span>
            <span>{SMELL_LABELS[type]}</span>
            <span className="chip-count">{run.smell_counts?.[type] ?? 0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
