// Centralny klient HTTP dla wszystkich wywołań API
import axios from "axios";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  withCredentials: true, // HttpOnly refresh cookie
  headers: { "Content-Type": "application/json" },
});

interface ApiErrorPayload {
  detail?: string;
  message?: string;
  details?: Array<{ field?: string; message?: string }>;
}

export function getApiErrorMessage(error: unknown): string {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) {
    return "Wystąpił nieoczekiwany błąd podczas zapisu.";
  }

  const payload = error.response?.data;
  if (payload?.details?.length) {
    return payload.details
      .map(({ field, message }) => {
        const fieldName = field?.replace(/^body\./, "");
        return fieldName ? `${fieldName}: ${message ?? "nieprawidłowa wartość"}` : message;
      })
      .filter(Boolean)
      .join(" · ");
  }

  if (payload?.message) return payload.message;
  if (payload?.detail) return payload.detail;
  if (!error.response) return "Nie udało się połączyć z API. Sprawdź, czy backend działa na porcie 8000.";
  return `Zapis nie powiódł się (HTTP ${error.response.status}).`;
}

// Wstrzyknięcie access tokena
api.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh przy 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const { data } = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true }
        );
        localStorage.setItem("access_token", data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ─── Typed API helpers ─────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; expires_in: number }>("/auth/login", {
      email,
      password,
    }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword }),
};

export const personsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/persons", { params }),
  get: (idOrSlug: string) => api.get(`/persons/${idOrSlug}`),
  create: (data: unknown) => api.post("/persons", data),
  update: (id: string, data: unknown) => api.patch(`/persons/${id}`, data),
  delete: (id: string) => api.delete(`/persons/${id}`),
  restore: (id: string) => api.post(`/persons/${id}/restore`),
  versions: (id: string) => api.get(`/persons/${id}/versions`),
};

export const geographyApi = {
  countries: (params?: Record<string, unknown>) =>
    api.get("/geography/countries", { params }),
  dioceses: (params?: Record<string, unknown>) =>
    api.get("/geography/dioceses", { params }),
  places: (params?: Record<string, unknown>) =>
    api.get("/geography/places", { params }),
  churches: (params?: Record<string, unknown>) =>
    api.get("/geography/churches", { params }),
};

export const ordersApi = {
  list: (params?: Record<string, unknown>) => api.get("/orders", { params }),
  create: (data: unknown) => api.post("/orders", data),
};

export const popesApi = {
  list: (params?: Record<string, unknown>) => api.get("/popes", { params }),
  create: (data: unknown) => api.post("/popes", data),
};

export const sourcesApi = {
  bibliography: (params?: Record<string, unknown>) =>
    api.get("/sources/bibliography", { params }),
  historicalSources: (params?: Record<string, unknown>) =>
    api.get("/sources/historical-sources", { params }),
  images: (params?: Record<string, unknown>) =>
    api.get("/sources/images", { params }),
  documents: (params?: Record<string, unknown>) =>
    api.get("/sources/documents", { params }),
};

export const taxonomyApi = {
  categories: () => api.get("/taxonomy/categories"),
  tags: (params?: Record<string, unknown>) =>
    api.get("/taxonomy/tags", { params }),
  statesOfLife: () => api.get("/taxonomy/states-of-life"),
  occupations: () => api.get("/taxonomy/occupations"),
};

export const usersApi = {
  list: (params?: Record<string, unknown>) => api.get("/users", { params }),
  create: (data: unknown) => api.post("/users", data),
  delete: (id: string) => api.delete(`/users/${id}`),
};
