import { useState, useEffect, useCallback } from "react";
import { authService, tokenStorage } from "../services/api";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({ user: null, loading: true, error: null });

  const fetchUser = useCallback(async () => {
    if (!tokenStorage.getAccess()) {
      setState({ user: null, loading: false, error: null });
      return;
    }
    try {
      const user = await authService.me();
      setState({ user, loading: false, error: null });
    } catch {
      tokenStorage.clear();
      setState({ user: null, loading: false, error: null });
    }
  }, []);

  useEffect(() => { fetchUser(); }, [fetchUser]);

  const login = async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      await authService.login(email, password);
      await fetchUser();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Login failed.";
      setState((s) => ({ ...s, loading: false, error: msg }));
      throw err;
    }
  };

  const logout = () => {
    authService.logout();
    setState({ user: null, loading: false, error: null });
  };


  return { ...state, login, logout, refetch: fetchUser };
}
