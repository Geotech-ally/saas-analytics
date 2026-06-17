import React, { useState } from "react";

interface ResetPasswordProps {
  onSubmit: (password: string, passwordConfirm: string) => Promise<void>;
  onNavigateToLogin: () => void;
  error: string | null;
  loading: boolean;
  success: boolean;
}

export default function ResetPassword({
  onSubmit,
  onNavigateToLogin,
  error,
  loading,
  success,
}: ResetPasswordProps) {
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || !passwordConfirm) return;
    await onSubmit(password, passwordConfirm);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">DataLens</span>
        </div>
        <h1 className="auth-title">Set new password</h1>
        {success ? (
          <div className="auth-success">
            <p>Your password has been reset successfully!</p>
            <button type="button" className="btn-primary btn-full" onClick={onNavigateToLogin}>
              Sign in
            </button>
          </div>
        ) : (
          <>
            <p className="auth-description">
              Enter your new password below.
            </p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <label>
                New Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                  minLength={8}
                />
              </label>
              <label>
                Confirm New Password
                <input
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                  minLength={8}
                />
              </label>
              {error && <p className="form-error">{error}</p>}
              <button type="submit" className="btn-primary btn-full" disabled={loading}>
                {loading ? "Resetting…" : "Reset password"}
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
