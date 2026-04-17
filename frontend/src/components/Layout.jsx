import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../App";
import { useTheme } from "./ThemeProvider";

const NAV = [
  { to: "/", icon: "\u25a6", label: "Dashboard" },
  { to: "/todo", icon: "\u2713", label: "Todo" },
  { to: "/gym", icon: "\u2666", label: "Gym" },
  { to: "/habits", icon: "\u2605", label: "Habits" },
  { to: "/pomodoro", icon: "\u23f1", label: "Pomodoro" },
  { to: "/notes", icon: "\u270e", label: "Notes" },
  { to: "/analytics", icon: "\u2261", label: "Analytics" },
  { to: "/settings", icon: "\u2699", label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>LIFE TRACKER</h1>
          <span>{user?.username}</span>
        </div>
        <nav className="nav-links">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}>
              <span className="nav-icon">{n.icon}</span>
              <span className="nav-label">{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="theme-toggle" onClick={toggle}>
          {theme === "dark" ? "\u2600" : "\u263e"}{" "}
          <span className="nav-label">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
        <button className="theme-toggle" onClick={handleLogout}>
          {"\u2192"} <span className="nav-label">Logout</span>
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
