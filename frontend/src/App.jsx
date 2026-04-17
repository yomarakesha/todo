import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect, createContext, useContext } from "react";
import { ToastProvider } from "./components/Toast";
import { ThemeProvider } from "./components/ThemeProvider";
import Layout from "./components/Layout";
import Dashboard from "./components/Dashboard";
import Todo from "./components/Todo";
import Gym from "./components/Gym";
import Habits from "./components/Habits";
import Pomodoro from "./components/Pomodoro";
import Notes from "./components/Notes";
import Analytics from "./components/Analytics";
import Settings from "./components/Settings";
import Auth from "./components/Auth";

const AuthCtx = createContext();

export function useAuth() {
  return useContext(AuthCtx);
}

function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        setUser({ id: payload.sub, username: payload.username });
      } catch {
        setUser(null);
      }
    } else {
      localStorage.removeItem("token");
      setUser(null);
    }
  }, [token]);

  const logout = () => setToken(null);

  return (
    <AuthCtx.Provider value={{ token, setToken, user, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

function ProtectedRoute({ children }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Auth />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="todo" element={<Todo />} />
                <Route path="gym" element={<Gym />} />
                <Route path="habits" element={<Habits />} />
                <Route path="pomodoro" element={<Pomodoro />} />
                <Route path="notes" element={<Notes />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;
