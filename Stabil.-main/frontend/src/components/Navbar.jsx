import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <div className="navbar">
      <h2 className="logo">STABIL.</h2>
      <div className="nav-links">
        <Link to="/">Home</Link>
        <Link to="/results">Results</Link>
        <Link to="/dashboard">Dashboard</Link>
      </div>
    </div>
  );
}
