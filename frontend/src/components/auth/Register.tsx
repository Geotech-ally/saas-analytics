import React, { useState } from "react";

interface RegisterProps {
  onRegister: (data: RegisterData) => Promise<void>;
  onNavigateToLogin: () => void;
  error: string | null;
  loading: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  organization_id: string;
}


export default function Register({ onRegister, onNavigateToLogin, error, loading }: RegisterProps) {
  const [formData, setFormData] = useState<RegisterData>({

    email: "",
    password: "",
    password_confirm: "",
    first_name: "",
    last_name: "",
    organization_id: "",
  });




  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Avoid sending empty string; backend will auto-create org when null/omitted.
    const organization_id = formData.organization_id?.trim() ? formData.organization_id : undefined as any;
    const payload: RegisterData = {
      ...formData,
      organization_id,
    };


    await onRegister(payload);
  };


  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">DataLens</span>
        </div>
        <h1 className="auth-title">Create your account</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <label>
              First Name
              <input
                type="text"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                placeholder="John"
                autoComplete="given-name"
                required
              />
            </label>
            <label>
              Last Name
              <input
                type="text"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                placeholder="Doe"
                autoComplete="family-name"
                required
              />
            </label>
          </div>
          <label>
            Email
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              autoComplete="new-password"
              required
              minLength={8}
            />
          </label>
            <label>
              Organization ID (optional)
              <input
                type="text"
                name="organization_id"
                value={formData.organization_id}
                onChange={handleChange}
                placeholder="UUID (e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6)"
                autoComplete="off"
              />
            </label>


          <label>
            Confirm Password
            <input
              type="password"
              name="password_confirm"
              value={formData.password_confirm}
              onChange={handleChange}
              placeholder="••••••••"
              autoComplete="new-password"
              required
              minLength={8}
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-primary btn-full" disabled={loading}>
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>
        <div className="auth-footer" style={{ marginTop: "18px" }}>
          <div style={{ textAlign: "center" }}>
            <span style={{ color: "var(--text-muted)", fontSize: 13, fontWeight: 600 }}>
              Already have an account?
            </span>
            <button
              type="button"
              className="link-button"
              onClick={onNavigateToLogin}
              aria-label="Sign in"
              style={{
                marginLeft: 6,
                color: "var(--accent)",
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "underline",
                cursor: "pointer",
                padding: 0,
              }}
            >
              Sign In
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
