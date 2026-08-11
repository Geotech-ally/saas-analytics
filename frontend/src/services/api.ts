import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

// ── Token storage ──────────────────────────────────────────────────────────
const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export const tokenStorage = {
  getAccess: () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ── Factory ────────────────────────────────────────────────────────────────
function createClient(baseURL: string): AxiosInstance {
  const client = axios.create({ baseURL, timeout: 15_000 });

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
          const refresh = tokenStorage.getRefresh();
          if (!refresh) throw new Error("No refresh token");
          const { data } = await axios.post(
            `${DJANGO_URL}/api/v1/auth/token/refresh/`,
            { refresh }
          );


          // Store rotated refresh token if provided by the backend.
          const nextAccess = data.access;
          const nextRefresh = data.refresh ?? refresh;
          if (!nextAccess) throw new Error("Refresh response missing access token");

          tokenStorage.set(nextAccess, nextRefresh);
          original.headers.Authorization = `Bearer ${nextAccess}`;

          return client(original);
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
const DJANGO_URL = "http://127.0.0.1:8000";
const FASTAPI_URL = "http://127.0.0.1:8001";



export const djangoAPI = createClient(DJANGO_URL);
export const analyticsAPI = createClient(FASTAPI_URL);



// ── Auth ───────────────────────────────────────────────────────────────────
export const authService = {
  login: async (email: string, password: string) => {
    const { data } = await djangoAPI.post("/api/v1/auth/login/", { email, password });
    tokenStorage.set(data.access, data.refresh);
    return data;
  },
  socialTokenExchange: async () => {
    const { data } = await djangoAPI.post("/api/v1/auth/social/token-exchange/");
    tokenStorage.set(data.access, data.refresh);
    return data;
  },


  register: async (payload: Record<string, unknown>) => {
    const res = await djangoAPI.post("/api/v1/auth/registration/", {
      email: payload.email,
      password1: payload.password,
      password2: payload.password_confirm,
      first_name: payload.first_name,
      last_name: payload.last_name,
      organization: payload.organization_id || null,
    });
    const data = res.data;
    if (res.status >= 400) {
      throw new Error(
        data.email?.[0] ||
        data.password1?.[0] ||
        data.non_field_errors?.[0] ||
        "Registration failed"
      );
    }
    tokenStorage.set(data.access, data.refresh);
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
    // Best-effort server-side logout/blacklist.
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) {
        await djangoAPI.post("/api/v1/auth/logout/", { refresh });
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
