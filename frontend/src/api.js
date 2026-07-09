const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function startAnalysis(url) {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Failed to start analysis");
  return res.json();
}

export async function getRun(runId) {
  const res = await fetch(`${BASE_URL}/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export async function requestFix(runId, smell) {
  const res = await fetch(`${BASE_URL}/runs/${runId}/fix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: smell.type, target: smell.target, path: smell.path }),
  });
  if (!res.ok) {
    let detail = "Failed to get a fix suggestion";
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    const error = new Error(detail);
    error.status = res.status;
    throw error;
  }
  return res.json();
}
