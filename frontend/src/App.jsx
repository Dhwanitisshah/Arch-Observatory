import { useState } from "react";
import "./App.css";
import { startAnalysis } from "./api";
import DependencyGraph from "./components/DependencyGraph";
import HealthHeader from "./components/HealthHeader";
import RunProgress from "./components/RunProgress";
import SmellTable from "./components/SmellTable";

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [analyzedUrl, setAnalyzedUrl] = useState("");
  const [runId, setRunId] = useState(null);
  const [run, setRun] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);

  const isActive = run && (run.status === "pending" || run.status === "running" || run.status === "failed");
  const isDone = run && run.status === "done";

  async function handleAnalyze() {
    if (!repoUrl.trim()) return;
    setSubmitError(null);
    setRun(null);
    setSelectedModule(null);
    try {
      const { run_id } = await startAnalysis(repoUrl);
      setAnalyzedUrl(repoUrl);
      setRunId(run_id);
      setRun({ status: "pending", stage: null });
    } catch (e) {
      setSubmitError(e.message);
    }
  }

  function handleReset() {
    setRunId(null);
    setRun(null);
    setSelectedModule(null);
    setSubmitError(null);
  }

  return (
    <div className="app">
      <div className="topbar">
        <h1>arch-observatory</h1>
        <input
          type="text"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
        />
        <button type="button" className="btn" onClick={handleAnalyze} disabled={isActive}>
          Analyze
        </button>
        {submitError && <span className="topbar-error">{submitError}</span>}
        {isDone && (
          <button type="button" className="btn btn-ghost" onClick={handleReset}>
            New analysis
          </button>
        )}
      </div>

      {isActive && (
        <RunProgress
          runId={runId}
          status={run.status}
          stage={run.stage}
          error={run.error}
          onUpdate={setRun}
          onReset={handleReset}
        />
      )}

      {isDone && (
        <>
          <HealthHeader run={run} repoUrl={analyzedUrl} />
          <div className="report">
            <div className="report-pane graph-pane">
              <DependencyGraph
                nodes={run.dependency_nodes}
                edges={run.dependency_edges}
                smells={run.smells}
                selectedModule={selectedModule}
                onSelectNode={setSelectedModule}
              />
            </div>
            <SmellTable
              smells={run.smells}
              selectedModule={selectedModule}
              onSelectModule={setSelectedModule}
              runId={runId}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default App;
