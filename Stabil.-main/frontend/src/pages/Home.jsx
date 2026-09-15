import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home">
      <div className="hero">
        <h1>Elevating Surgical Precision, with STABIL.</h1>
        <div className="hero-buttons">
          <button onClick={() => navigate("/train")}>
            START PRACTICE
          </button>
          <button onClick={() => navigate("/dashboard")}>
            VIEW STATISTICS
          </button>
        </div>
      </div>
    </div>
  );
}
