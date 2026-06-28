import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useLogin } from "../hooks/useLogin";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { handleLogin, error, isLoading } = useLogin();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleLogin(email, password);
  };

  return (
    <form className="auth-form" onSubmit={onSubmit} noValidate>
      <div style={{ textAlign: "center", marginBottom: "8px" }}>
        <div style={{
          width: "48px",
          height: "48px",
          background: "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
          borderRadius: "12px",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "16px",
          boxShadow: "0 4px 12px rgba(13, 148, 136, 0.25)",
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </div>
      </div>
      <h1 className="auth-title" style={{ textAlign: "center" }}>Welcome Back</h1>
      <p className="auth-subtitle" style={{ textAlign: "center" }}>Sign in to your iClinic account</p>

      {error && (
        <div className="auth-error" role="alert">
          {error}
        </div>
      )}

      <div className="form-group">
        <label htmlFor="email">Email Address</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          required
          autoComplete="email"
          autoFocus
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
          autoComplete="current-password"
        />
      </div>

      <button type="submit" className="auth-btn" disabled={isLoading}>
        {isLoading ? "Signing in..." : "Sign In"}
      </button>

      <p className="auth-footer">
        Don't have an account? <Link to="/register">Create one</Link>
      </p>
    </form>
  );
}
