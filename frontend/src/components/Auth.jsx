import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { api } from "../api";

export default function Auth() {
  const [tab, setTab] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { setToken } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const fn = tab === "login" ? api.login : api.register;
      const res = await fn({ username, password });
      if (res.token) {
        setToken(res.token);
        navigate("/");
      } else {
        setError(res.detail || "Something went wrong");
      }
    } catch {
      setError("Connection error");
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>LIFE TRACKER</h1>
        <p>Track your productivity</p>

        <div className="auth-tabs">
          <button className={tab === "login" ? "active" : ""} onClick={() => setTab("login")}>
            Login
          </button>
          <button className={tab === "register" ? "active" : ""} onClick={() => setTab("register")}>
            Register
          </button>
        </div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", padding: "12px", marginTop: 8 }}
          >
            {tab === "login" ? "Login" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
