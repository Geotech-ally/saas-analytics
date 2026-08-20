import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

// ── Token storage (sessionStorage limits XSS exposure to tab lifetime) ──────
const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export const tokenStorage = {
  getAccess: () => sessionStorage.getItem(TOKEN_KEY),
  getRefresh: () => sessionStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    sessionStorage.setItem(TOKEN_KEY, access);
    sessionStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  },
};

// ── Factory ────────────────────────────────────────────────────────────────
function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({ baseURL, timeout: 15_000, withCredentials: true });

  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccess();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    async (error) => {
      const original = error.config;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        try {
          // Primary: cookie-based refresh (backend reads refresh token from HttpOnly cookie).
          // Fallback: body-based refresh using sessionStorage for backward compatibility.
          let refreshed = false;
          try {
            const { data } = await axios.post(
              `${DJANGO_URL}/api/v1/auth/token/refresh/`,
              {},
              { withCredentials: true }
            );
            const nextAccess = data.access;
            if (nextAccess) {
              tokenStorage.set(nextAccess, data.refresh ?? tokenStorage.getRefresh() ?? "");
              original.headers.Authorization = `Bearer ${nextAccess}`;
              refreshed = true;
            }
          } catch {
            const refresh = tokenStorage.getRefresh();
            if (!refresh) throw new Error("No refresh token available");
            const { data } = await axios.post(
              `${DJANGO_URL}/api/v1/auth/token/refresh/`,
              { refresh },
              { withCredentials: true }
            );
            const nextAccess = data.access;
            if (!nextAccess) throw new Error("Refresh response missing access token");
            tokenStorage.set(nextAccess, data.refresh ?? refresh);
            original.headers.Authorization = `Bearer ${nextAccess}`;
            refreshed = true;
          }

          if (refreshed) {
            return client(original);
          }
        } catch {
          tokenStorage.clear();
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

// ── Clients ────────────────────────────────────────────────────────────────
// In Docker/production these come from the VITE_DJANGO_URL / VITE_FASTAPI_URL
// build args in docker-compose.yml (e.g. "/api/django", "/api/analytics"),
// which nginx.conf then reverse-proxies to the django/fastapi containers.
// The relative-path fallbacks match the dev-server proxy rules in vite.config.ts,
// so `npm run dev` works too.
const DJANGO_URL = import.meta.env.VITE_DJANGO_URL ?? "/api/django";
const FASTAPI_URL = import.meta.env.VITE_FASTAPI_URL ?? "/api/analytics";



export const djangoAPI = createClient(DJANGO_URL);
export const analyticsAPI = createClient(FASTAPI_URL);



// ── Auth ───────────────────────────────────────────────────────────────────
export const authService = {
  login: async (email: string, password: string) => {
    const { data } = await djangoAPI.post("/api/v1/auth/token/", { email, password });
    tokenStorage.set(data.access, data.refresh);
    return data;
  },
  socialTokenExchange: async () => {
    const { data } = await djangoAPI.post("/api/v1/auth/social/token-exchange/");
    tokenStorage.set(data.access, data.refresh);
    return data;
  },

  register: async (payload: Record<string, unknown>) => {
    const mapped = {
      ...payload,
      ...(payload.password ? { password1: payload.password } : {}),
      ...(payload.password_confirm ? { password2: payload.password_confirm } : {}),
    };
    const { data } = await djangoAPI.post("/api/v1/auth/register/", mapped);
    return data;
  },
  forgotPassword: async (email: string) => {
    const { data } = await djangoAPI.post("/api/v1/auth/forgot-password/", { email });
    return data;
  },
  resetPassword: async (uid: string, token: string, new_password: string, new_password_confirm: string) => {
    const { data } = await djangoAPI.post("/api/v1/auth/reset-password/", {
      uid,
      token,
      new_password,
      new_password_confirm,
    });
    return data;
  },
  logout: async () => {
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) {
        await djangoAPI.post("/api/v1/auth/logout/", { refresh }, { withCredentials: true });
      }
    } catch {
      // Ignore network/server errors; still clear local tokens.
    }
    tokenStorage.clear();
  },

  me: async () => {
    const { data } = await djangoAPI.get("/api/v1/users/me/");
    return data;
  },
};

// ── Users ──────────────────────────────────────────────────────────────────
export const usersService = {
  list: async () => (await djangoAPI.get("/api/v1/users/")).data,
  update: async (payload: Record<string, unknown>) =>
    (await djangoAPI.patch("/api/v1/users/me/", payload)).data,
  changePassword: async (payload: Record<string, string>) =>
    (await djangoAPI.post("/api/v1/users/change_password/", payload)).data,
};

// ── Datasets ───────────────────────────────────────────────────────────────
export const datasetsService = {
  list: async () => (await djangoAPI.get("/api/v1/datasets/")).data,
  upload: async (form: FormData) =>
    (await djangoAPI.post("/api/v1/datasets/", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })).data,
  delete: async (id: string) => djangoAPI.delete(`/api/v1/datasets/${id}/`),
};

// ── Analytics ──────────────────────────────────────────────────────────────
export const analyticsService = {
  getAnalytics: async (datasetId: string) =>
    (await analyticsAPI.get(`/api/v1/analytics/${datasetId}`)).data,
  getKPI: async (datasetId: string) =>
    (await analyticsAPI.get(`/api/v1/analytics/${datasetId}/kpi`)).data,
  getInsights: async (datasetId: string) =>
    (await analyticsAPI.get(`/api/v1/analytics/${datasetId}/insights`)).data,
};
