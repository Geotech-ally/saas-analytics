import React, { useState } from "react";

interface ForgotPasswordProps {
  onSubmit: (email: string) => Promise<void>;
  onNavigateToLogin: () => void;
  error: string | null;
  loading: boolean;
  success: boolean;
}

export default function ForgotPassword({
  onSubmit,
  onNavigateToLogin,
  error,
  loading,
  success,
}: ForgotPasswordProps) {
  const [email, setEmail] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    await onSubmit(email);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">DataLens</span>
        </div>
        <h1 className="auth-title">Reset your password</h1>
        {success ? (
          <div className="auth-success">
            <p>
              If an account exists with this email, a password reset link has been sent.
              Please check your inbox.
            </p>
            <button type="button" className="btn-primary btn-full" onClick={onNavigateToLogin}>
              Back to Sign in
            </button>
          </div>
        ) : (
          <>
            <p className="auth-description">
              Enter your email address and we'll send you a link to reset your password.
            </p>
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
              {error && <p className="form-error">{error}</p>}
              <button type="submit" className="btn-primary btn-full" disabled={loading}>
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <div className="auth-footer" style={{ marginTop: "18px", textAlign: "center" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "var(--text-muted)", fontSize: 13, fontWeight: 700 }}>
                  Back to Sign in
                </span>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={onNavigateToLogin}
                  aria-label="Sign in"
                  style={{
                    padding: "6px 12px",
                    fontWeight: 700,
                    color: "var(--accent)",
                    textDecoration: "underline",
                  }}
                >
                  Sign In
                </button>

              </div>
            </div>

          </>
        )}
      </div>
    </div>
  );
}
