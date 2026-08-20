import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function LoginPage() {
  const { authenticated, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (authenticated) return <Navigate to="/dashboard" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard", { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="login-story">
        <span className="eyebrow">E-commerce signal engine</span>
        <h1>Find the products worth a closer look.</h1>
        <p>Amazon velocity, Google demand, historical wins, and explainable scoring in one focused workspace.</p>
        <div className="story-stat"><strong>6h</strong><span>automatic collection cadence</span></div>
      </section>
      <section className="login-panel">
        <form className="auth-card" onSubmit={submit}>
          <div className="brand-mark large">LB</div>
          <div>
            <span className="eyebrow">Protected workspace</span>
            <h2>Welcome back</h2>
            <p>Sign in to review product opportunities.</p>
          </div>
          <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="alert alert-error">{error}</div>}
          <button className="button button-primary full" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button>
        </form>
      </section>
    </div>
  );
}
