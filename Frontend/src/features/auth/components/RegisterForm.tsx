import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useRegister } from "../hooks/useRegister";

export function RegisterForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("PATIENT");
  const { handleRegister, error, isLoading } = useRegister();
  const [localError, setLocalError] = useState<string | null>(null);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (password !== confirmPassword) {
      setLocalError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setLocalError("Password must be at least 8 characters");
      return;
    }

    handleRegister(email, password, role);
  };

  const displayError = localError || error;

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
      <h1 className="auth-title" style={{ textAlign: "center" }}>Create Account</h1>
      <p className="auth-subtitle" style={{ textAlign: "center" }}>Join iClinic for easy healthcare access</p>

      {displayError && (
        <div className="auth-error" role="alert">
          {displayError}
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

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 8 characters"
            required
            autoComplete="new-password"
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm</label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Re-enter password"
            required
            autoComplete="new-password"
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="role">I am a</label>
        <select
          id="role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="PATIENT">Patient</option>
          <option value="DOCTOR">Doctor</option>
        </select>
      </div>

      <button type="submit" className="auth-btn" disabled={isLoading}>
        {isLoading ? "Creating account..." : "Create Account"}
      </button>

      <p className="auth-footer">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </form>
  );
}
