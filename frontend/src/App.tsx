import { useEffect, useState } from "react";

import { useAuth } from "./hooks/useAuth";

import Login from "./components/auth/Login";
import Register from "./components/auth/Register";
import ForgotPassword from "./components/auth/ForgotPassword";
import ResetPassword from "./components/auth/ResetPassword";
import Dashboard from "./components/dashboard/Dashboard";
import { authService } from "./services/api";
import type { RegisterData } from "./components/auth/Register";
import "./styles/globals.css";

type AuthPage = "login" | "register" | "forgot-password" | "reset-password";




export default function App() {
  const { user, loading, error, login, logout } = useAuth();
  const [authPage, setAuthPage] = useState<AuthPage>("login");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [forgotPasswordSuccess, setForgotPasswordSuccess] = useState(false);
  const [resetPasswordSuccess, setResetPasswordSuccess] = useState(false);

  // Get reset password params from URL
  const urlParams = new URLSearchParams(window.location.search);
  const resetUid = urlParams.get("uid");
  const resetToken = urlParams.get("token");

  // Auto-navigate to reset password page if params are present
  // (must be in an effect to avoid state updates during render)
  useEffect(() => {
    if (resetUid && resetToken && authPage !== "reset-password") {
      setAuthPage("reset-password");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetUid, resetToken]);

  // Social login (Google/Microsoft): allauth completes OAuth server-side.
  // On return, we attempt to exchange Django session -> JWT.
  useEffect(() => {
    const exchange = async () => {
      try {
        await authService.socialTokenExchange();
      } catch {
        // If we are not in a social-authenticated session, ignore.
      }
    };

    exchange();
  }, []);





  const handleRegister = async (data: RegisterData) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await authService.register({
        email: data.email,
        password: data.password,
        password_confirm: data.password_confirm,
        first_name: data.first_name,
        last_name: data.last_name,
        // Omit organization_id when empty so backend can auto-create.
        ...(data.organization_id?.trim() ? { organization_id: data.organization_id } : {}),
      } as any);


      // After successful registration, log them in
      await login(data.email, data.password);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string; email?: string[]; password?: string[] } } })
        ?.response?.data?.detail 
        || (err as { response?: { data?: { email?: string[] } } })?.response?.data?.email?.[0]
        || (err as { response?: { data?: { password?: string[] } } })?.response?.data?.password?.[0]
        || "Registration failed.";
      setAuthError(msg);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleForgotPassword = async (email: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      await authService.forgotPassword(email);
      setForgotPasswordSuccess(true);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to send reset email.";
      setAuthError(msg);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleResetPassword = async (password: string, passwordConfirm: string) => {
    if (!resetUid || !resetToken) {
      setAuthError("Invalid reset link.");
      return;
    }

    setAuthLoading(true);
    setAuthError(null);
    try {
      await authService.resetPassword(resetUid, resetToken, password, passwordConfirm);
      setResetPasswordSuccess(true);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Failed to reset password.";
      setAuthError(msg);
    } finally {
      setAuthLoading(false);
    }
  };

  const navigateToLogin = () => {
    setAuthPage("login");
    setAuthError(null);
    setForgotPasswordSuccess(false);
    setResetPasswordSuccess(false);
    // Clear URL params
    window.history.replaceState({}, document.title, window.location.pathname);
  };

  const navigateToRegister = () => {
    setAuthPage("register");
    setAuthError(null);
  };

  const navigateToForgotPassword = () => {
    setAuthPage("forgot-password");
    setAuthError(null);
    setForgotPasswordSuccess(false);
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner spinner--lg" />
      </div>
    );
  }

  if (!user) {
    if (authPage === "register") {
      return (
        <Register
          onRegister={handleRegister}
          onNavigateToLogin={navigateToLogin}
          error={authError}
          loading={authLoading}
        />
      );
    }

    if (authPage === "forgot-password") {
      return (
        <ForgotPassword
          onSubmit={handleForgotPassword}
          onNavigateToLogin={navigateToLogin}
          error={authError}
          loading={authLoading}
          success={forgotPasswordSuccess}
        />
      );
    }

    if (authPage === "reset-password") {
      return (
        <ResetPassword
          onSubmit={handleResetPassword}
          onNavigateToLogin={navigateToLogin}
          error={authError}
          loading={authLoading}
          success={resetPasswordSuccess}
        />
      );
    }

    return (
      <Login
        onLogin={login}
        onNavigateToRegister={navigateToRegister}
        onNavigateToForgotPassword={navigateToForgotPassword}
        error={error}
        loading={loading}
      />
    );
  }

  return <Dashboard userEmail={user.email} onLogout={logout} />;
}
