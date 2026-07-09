import ReactMarkdown from "react-markdown";
import { requestFix } from "../api";

export default function FixPanel({ runId, smell, cacheEntry, onResult }) {
  const loading = cacheEntry?.status === "loading";
  const error = cacheEntry?.status === "error" ? cacheEntry.error : null;
  const result = cacheEntry?.status === "done" ? cacheEntry : null;

  async function handleClick() {
    onResult({ status: "loading" });
    try {
      const data = await requestFix(runId, smell);
      onResult({ status: "done", suggestion: data.suggestion, cached: data.cached, model: data.model });
    } catch (e) {
      onResult({ status: "error", error: e });
    }
  }

  return (
    <div className="fix-panel">
      {!result && !loading && !error && (
        <button type="button" className="btn" onClick={handleClick}>
          Suggest a fix
        </button>
      )}

      {loading && <div className="fix-panel-loading">Asking the model…</div>}

      {error && (
        <div className="fix-panel-error">
          {error.status === 503
            ? "LLM fix suggestions aren't configured for this deployment."
            : error.status === 502
              ? "The model failed to produce a suggestion. Try again in a moment."
              : error.message || "Something went wrong requesting a fix."}
          <button type="button" className="btn btn-ghost" onClick={handleClick}>
            Retry
          </button>
        </div>
      )}

      {result && (
        <div className="fix-panel-result">
          {result.cached && <span className="fix-panel-cached">cached</span>}
          <div className="fix-panel-markdown">
            <ReactMarkdown>{result.suggestion}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
