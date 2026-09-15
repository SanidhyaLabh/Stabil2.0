import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

export default function Train() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [topCamUrl, setTopCamUrl] = useState("http://192.168.1.3:8080/video");
  const [sideCamUrl, setSideCamUrl] = useState("http://10.234.207.98:8080/video");
  const [topStatus, setTopStatus] = useState(null);
  const [sideStatus, setSideStatus] = useState(null);
  const [testingTop, setTestingTop] = useState(false);
  const [testingSide, setTestingSide] = useState(false);

  useEffect(() => {
    const savedTop = localStorage.getItem("stabil_top_cam_ip");
    const savedSide = localStorage.getItem("stabil_side_cam_ip");
    if (savedTop !== null) setTopCamUrl(savedTop);
    if (savedSide !== null) setSideCamUrl(savedSide);
  }, []);

  const handleTopChange = (e) => {
    const val = e.target.value;
    setTopCamUrl(val);
    localStorage.setItem("stabil_top_cam_ip", val);
    setTopStatus(null);
  };

  const handleSideChange = (e) => {
    const val = e.target.value;
    setSideCamUrl(val);
    localStorage.setItem("stabil_side_cam_ip", val);
    setSideStatus(null);
  };

  const testCamera = async (type) => {
    const isTop = type === "top";
    const url = isTop ? topCamUrl : sideCamUrl;
    if (isTop) setTestingTop(true);
    else setTestingSide(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/api/check_camera", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (isTop) setTopStatus(data);
      else setSideStatus(data);
    } catch (err) {
      const errObj = { reachable: false, message: `Network error: ${err.message}` };
      if (isTop) setTopStatus(errObj);
      else setSideStatus(errObj);
    } finally {
      if (isTop) setTestingTop(false);
      else setTestingSide(false);
    }
  };

  const startTraining = async (mode) => {
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mode,
          top_cam_url: topCamUrl.trim(),
          side_cam_url: sideCamUrl.trim(),
        }),
      });

      const data = await res.json();
      localStorage.setItem("sessionData", JSON.stringify(data));
      setLoading(false);
      navigate("/results");
    } catch (err) {
      alert(`Error starting tracking session: ${err.message}`);
      setLoading(false);
    }
  };

  return (
    <div className="train-page" style={{ padding: "30px", maxWidth: "900px", margin: "0 auto" }}>
      <h1>Select Training Program</h1>

      {/* Camera Configuration Section */}
      <div className="camera-config" style={{ background: "#1e2230", padding: "20px", borderRadius: "12px", marginBottom: "30px", color: "#fff" }}>
        <h2>📹 Camera Source Setup</h2>
        <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "15px" }}>
          Configure top view and side view mobile IP webcam addresses or hardware webcam indices.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          {/* Top Camera */}
          <div style={{ background: "#161922", padding: "15px", borderRadius: "8px" }}>
            <label style={{ fontWeight: 600, display: "block", marginBottom: "8px" }}>
              Top View Camera (Primary)
            </label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <input
                type="text"
                value={topCamUrl}
                onChange={handleTopChange}
                placeholder="192.168.1.3:8080 or 0"
                style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid #334155", background: "#0f1117", color: "#fff" }}
              />
              <button
                type="button"
                onClick={() => testCamera("top")}
                disabled={testingTop}
                style={{ padding: "8px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer" }}
              >
                {testingTop ? "Testing..." : "Test"}
              </button>
            </div>
            {topStatus && (
              <p style={{ fontSize: "12px", color: topStatus.reachable ? "#4ade80" : "#f87171", margin: "4px 0 0 0" }}>
                {topStatus.reachable ? "✅ " : "❌ "} {topStatus.message}
              </p>
            )}
          </div>

          {/* Side Camera */}
          <div style={{ background: "#161922", padding: "15px", borderRadius: "8px" }}>
            <label style={{ fontWeight: 600, display: "block", marginBottom: "8px" }}>
              Side View Camera (Depth/Tilt)
            </label>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <input
                type="text"
                value={sideCamUrl}
                onChange={handleSideChange}
                placeholder="10.234.207.98:8080 or 1"
                style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid #334155", background: "#0f1117", color: "#fff" }}
              />
              <button
                type="button"
                onClick={() => testCamera("side")}
                disabled={testingSide}
                style={{ padding: "8px 14px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer" }}
              >
                {testingSide ? "Testing..." : "Test"}
              </button>
            </div>
            {sideStatus && (
              <p style={{ fontSize: "12px", color: sideStatus.reachable ? "#4ade80" : "#f87171", margin: "4px 0 0 0" }}>
                {sideStatus.reachable ? "✅ " : "❌ "} {sideStatus.message}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Program Selection Buttons */}
      <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
        <button
          onClick={() => startTraining("line")}
          disabled={loading}
          style={{ padding: "14px 24px", fontSize: "16px", background: "#1f2937", color: "#fff", border: "1px solid #374151", borderRadius: "8px", cursor: "pointer" }}
        >
          Incision Training
        </button>

        <button
          onClick={() => startTraining("circle")}
          disabled={loading}
          style={{ padding: "14px 24px", fontSize: "16px", background: "#1f2937", color: "#fff", border: "1px solid #374151", borderRadius: "8px", cursor: "pointer" }}
        >
          Circle Precision Training
        </button>

        <button
          onClick={() => startTraining("brain")}
          disabled={loading}
          style={{ padding: "14px 24px", fontSize: "16px", background: "#1f2937", color: "#fff", border: "1px solid #374151", borderRadius: "8px", cursor: "pointer" }}
        >
          Brain Path Navigation
        </button>

        <button
          onClick={() => startTraining("micro")}
          disabled={loading}
          style={{ padding: "14px 24px", fontSize: "16px", background: "#1f2937", color: "#fff", border: "1px solid #374151", borderRadius: "8px", cursor: "pointer" }}
        >
          Microsurgery Stability
        </button>
      </div>

      {loading && <p style={{ marginTop: "20px", fontWeight: "bold" }}>Training Session Active / Running...</p>}
    </div>
  );
}
