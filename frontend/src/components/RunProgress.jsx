import { useEffect, useRef } from "react";
import { getRun } from "../api";

const STAGE_KEYS = ["cloning", "metrics", "dependency_graph", "smells", "done"];

const STAGE_LABELS = {
  cloning: "Cloning repository",
  metrics: "Computing metrics",
  dependency_graph: "Building dependency graph",
  smells: "Detecting smells",
  done: "Done",
};

export default function RunProgress({ runId, status, stage, error, onUpdate, onReset }) {
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (!runId) return undefined;
    let cancelled = false;

    async function tick() {
      try {
        const doc = await getRun(runId);
        if (cancelled) return;
        onUpdate(doc);
        if (doc.status === "pending" || doc.status === "running") {
          timeoutRef.current = setTimeout(tick, 1500);
        }
      } catch (e) {
        if (!cancelled) onUpdate({ status: "failed", error: e.message });
      }
    }

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timeoutRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  if (status === "failed") {
    return (
      <div className="progress-wrap">
        <div className="error-card">
          <h3>Analysis failed</h3>
          <p>{error || "Something went wrong while analyzing this repository."}</p>
          <button type="button" className="btn" onClick={onReset}>
            Try another repo
          </button>
        </div>
      </div>
    );
  }

  const currentIndex = status === "done" ? STAGE_KEYS.length : stage ? STAGE_KEYS.indexOf(stage) : -1;

  return (
    <div className="progress-wrap">
      <div className="run-progress">
        <ol className="stage-list">
          {STAGE_KEYS.map((key, i) => {
            const state = status === "done" || i < currentIndex ? "complete" : i === currentIndex ? "active" : "pending";
            return (
              <li key={key} className={`stage stage-${state}`}>
                <span className="stage-marker">
                  {state === "complete" ? "✓" : state === "active" ? <span className="spinner" /> : i + 1}
                </span>
                <span className="stage-label">{STAGE_LABELS[key]}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
