import { useEffect, useRef, useState } from "react";
import { getRun, startAnalysis } from "./api";
import DependencyGraph from "./components/DependencyGraph";

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [runId, setRunId] = useState(null);
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => () => clearTimeout(pollRef.current), []);

  async function handleAnalyze() {
    setError(null);
    setRun(null);
    setSelectedModule(null);
    try {
      const { run_id } = await startAnalysis(repoUrl);
      setRunId(run_id);
      poll(run_id);
    } catch (e) {
      setError(e.message);
    }
  }

  function poll(id) {
    getRun(id)
      .then((doc) => {
        setRun(doc);
        if (doc.status === "pending" || doc.status === "running") {
          pollRef.current = setTimeout(() => poll(id), 1500);
        }
      })
      .catch((e) => setError(e.message));
  }

  const isDone = run?.status === "done";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "sans-serif" }}>
      <div style={{ padding: 12, display: "flex", gap: 8, alignItems: "center" }}>
        <h1 style={{ fontSize: 18, margin: 0 }}>arch-observatory</h1>
        <input
          type="text"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          style={{ flex: 1, maxWidth: 400 }}
        />
        <button type="button" onClick={handleAnalyze}>
          Analyze
        </button>
        {run && <span>status: {run.status}{run.stage ? ` (${run.stage})` : ""}</span>}
        {error && <span style={{ color: "red" }}>{error}</span>}
      </div>
      <div style={{ flex: 1, background: "#0f172a" }}>
        {isDone && (
          <DependencyGraph
            nodes={run.dependency_nodes}
            edges={run.dependency_edges}
            smells={run.smells}
            selectedModule={selectedModule}
            onSelectNode={setSelectedModule}
          />
        )}
      </div>
    </div>
  );
}

export default App;
