import { useState } from "react";

function App() {
  const [repoUrl, setRepoUrl] = useState("");

  return (
    <div>
      <h1>arch-observatory</h1>
      <div>
        <input
          type="text"
          placeholder="Analyze a repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
        />
        <button type="button">Analyze</button>
      </div>
    </div>
  );
}

export default App;
