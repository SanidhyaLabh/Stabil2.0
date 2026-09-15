import { useEffect, useState } from "react";

export default function Result() {
  const [result, setResult] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem("sessionData");
    if (stored) {
      setResult(JSON.parse(stored));
    }
  }, []);

  if (!result) return <h2>No Session Data</h2>;

  return (
    <div className="result-page">
      <h1>PSI Score: {result.analysis.psi_score}</h1>

      <div className="cards">
        <div className="card">
          <h3>Tremor</h3>
          <p>{result.analysis.tremor}</p>
        </div>

        <div className="card">
          <h3>Error</h3>
          <p>{result.analysis.error}</p>
        </div>

        <div className="card">
          <h3>Depth Error</h3>
          <p>{result.analysis.depth_error}</p>
        </div>
      </div>
    </div>
  );
}
