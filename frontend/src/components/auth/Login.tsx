import React, { useState } from "react";

interface LoginProps {

  onLogin: (email: string, password: string) => Promise<void>;
  onNavigateToRegister: () => void;
  onNavigateToForgotPassword: () => void;
  error: string | null;
  loading: boolean;
}

export default function Login({ onLogin, onNavigateToRegister, onNavigateToForgotPassword, error, loading }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    await onLogin(email, password);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">DataLens</span>
        </div>
        <h1 className="auth-title">Sign in to your workspace</h1>

        <div className="auth-social">
          <button
            type="button"
            className="btn-social btn-social--google btn-full"
            onClick={() => (window.location.href = "/accounts/google/login/")}
            disabled={loading}
          >
            Continue with Google
          </button>
          <button
            type="button"
            className="btn-social btn-social--microsoft btn-full"
            onClick={() => (window.location.href = "/accounts/microsoft/login/")}
            disabled={loading}
          >
            Continue with Microsoft
          </button>

          <div className="auth-divider">or continue with email</div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </label>

          <div style={{ textAlign: "right", marginTop: "-0.5rem" }}>
            <button type="button" className="link-button" onClick={onNavigateToForgotPassword}>
              Forgot password?
            </button>
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-primary btn-full" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="auth-footer">
          <span>Don't have an account?</span>
          <button
            type="button"
            className="link-button"
            onClick={onNavigateToRegister}
            aria-label="Sign up"
            style={{ textDecoration: "underline", fontWeight: 700, color: "#6366f1" }}
          >
            Sign up
          </button>
        </div>

      </div>
    </div>
  );
}
