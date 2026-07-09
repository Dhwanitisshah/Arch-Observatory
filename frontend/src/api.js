const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}
