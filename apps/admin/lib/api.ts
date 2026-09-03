// Centralny klient HTTP dla wszystkich wywołań API
import axios from "axios";
import type { AiDashboard, AiSuggestionsResponse } from "@/lib/ai";
import type {
  CreateRolePayload,
  CreateUserPayload,
  ManagedRole,
  ManagedUser,
  ManagedUsersResponse,
  RolesResponse,
  UpdateRolePayload,
  UpdateUserPayload,
} from "@/lib/access-control";
import type {
  EditorialDashboard,
  EditorialPriority,
  EditorialQualityReport,
  EditorialQueueResponse,
  PublicationStatus,
} from "@/lib/editorial";
import type { ApplicationSettings, UserProfile } from "@/lib/settings";
import { useAuthStore } from "@/lib/store/auth";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  withCredentials: true, // HttpOnly refresh cookie
  headers: { "Content-Type": "application/json" },
});

interface ApiErrorPayload {
  error?: string;
  detail?: string | { message?: string; errors?: string[] } | Array<unknown>;
  message?: string;
  details?: Array<{ field?: string; message?: string }>;
  request_id?: string | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post<TokenResponse>(
        `${API_BASE_URL}/api/v1/auth/refresh`,
        {},
        { withCredentials: true },
      )
      .then(({ data }) => {
        useAuthStore.getState().setAccessToken(data.access_token);
        return data.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
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
  if (typeof payload?.detail === "string") return payload.detail;
  if (payload?.detail && !Array.isArray(payload.detail) && typeof payload.detail === "object") {
    const detailMessage = payload.detail.message;
    const detailErrors = payload.detail.errors;
    return [detailMessage, ...(detailErrors ?? [])].filter(Boolean).join(" · ") || "API zwróciło nieprawidłowe dane.";
  }
  if (!error.response) return "Nie udało się połączyć z API. Sprawdź, czy backend działa na porcie 8000.";
  return `Zapis nie powiódł się (HTTP ${error.response.status}).`;
}

// Access token lives only in memory. The persistent session is the HttpOnly cookie.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh przy 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const requestUrl = original?.url ?? "";
    const isAuthenticationRequest =
      requestUrl.endsWith("/auth/login") ||
      requestUrl.endsWith("/auth/refresh");

    // A rejected login must reach the form unchanged so it can display the
    // API error. Refreshing here caused a second 401 and an immediate reload,
    // which made the original request and message appear to disappear.
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthenticationRequest
    ) {
      original._retry = true;
      try {
        const accessToken = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${accessToken}`;
        return api(original);
      } catch {
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") window.location.replace("/login");
      }
    }
    return Promise.reject(error);
  }
);

// ─── Typed API helpers ─────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", {
      email,
      password,
    }),
  refresh: () => refreshAccessToken(),
  logout: () => api.post("/auth/logout"),
  me: () => api.get<UserProfile>("/auth/me"),
  updateProfile: (data: { full_name?: string; preferred_language?: string }) =>
    api.patch<UserProfile>("/auth/me", data),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword }),
};

export const personsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/persons", { params }),
  adminList: (params?: Record<string, unknown>) =>
    api.get("/persons/admin", { params }),
  get: (idOrSlug: string) => api.get(`/persons/admin/${idOrSlug}`),
  create: (data: unknown) => api.post("/persons", data),
  update: (id: string, data: unknown) => api.patch(`/persons/${id}`, data),
  delete: (id: string) => api.delete(`/persons/${id}`),
  restore: (id: string) => api.post(`/persons/${id}/restore`),
  versions: (id: string) => api.get(`/persons/${id}/versions`),
};

export const editorialApi = {
  dashboard: () => api.get<EditorialDashboard>("/editorial/dashboard"),
  quality: () => api.get<EditorialQualityReport>("/editorial/quality"),
  queue: (params?: {
    page?: number;
    per_page?: number;
    search?: string;
    status?: "draft" | "review";
    priority?: EditorialPriority;
    attention?: boolean;
  }) => api.get<EditorialQueueResponse>("/editorial/queue", { params }),
  transition: (id: string, targetStatus: PublicationStatus, expectedVersion: number, note?: string) =>
    api.post(`/editorial/queue/${id}/transition`, {
      target_status: targetStatus,
      expected_version: expectedVersion,
      ...(note ? { note } : {}),
    }),
};

export const aiApi = {
  dashboard: () => api.get<AiDashboard>("/ai/dashboard"),
  suggestions: (params?: {
    limit?: number;
    kind?: "embedding" | "summary" | "tags";
    status?: "pending_review" | "ready_to_generate" | "blocked";
  }) => api.get<AiSuggestionsResponse>("/ai/suggestions", { params }),
  generateEmbedding: (personId: string) => api.post(`/ai/embeddings/${personId}`),
  generateSummary: (personId: string, maxWords = 100) =>
    api.post(`/ai/summarize/${personId}`, null, { params: { max_words: maxWords } }),
  generateTags: (personId: string) => api.post(`/ai/tag/${personId}`),
  batchEmbeddings: (params?: { overwrite_existing?: boolean; batch_size?: number }) =>
    api.post("/ai/batch/embed", null, { params }),
  batchTags: (params?: { only_untagged?: boolean }) =>
    api.post("/ai/batch/tag", null, { params }),
};

export const settingsApi = {
  get: () => api.get<ApplicationSettings>("/settings"),
};

export const calendarApi = {
  calendars: () => api.get("/calendar/calendars"),
  personEntries: (personId: string) =>
    api.get(`/calendar/persons/${personId}/entries`),
  createEntry: (data: unknown) => api.post("/calendar/entries", data),
  updateEntry: (entryId: string, data: unknown) =>
    api.patch(`/calendar/entries/${entryId}`, data),
  deleteEntry: (entryId: string) => api.delete(`/calendar/entries/${entryId}`),
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
  personSources: (personId: string) =>
    api.get(`/sources/person-links/${personId}`),
  assignPersonSource: (personId: string, data: unknown) =>
    api.post(`/sources/person-links/${personId}`, data),
  createPersonWebSource: (personId: string, data: unknown) =>
    api.post(`/sources/person-links/${personId}/web`, data),
  removePersonSource: (personId: string, linkId: string) =>
    api.delete(`/sources/person-links/${personId}/${linkId}`),
  images: (params?: Record<string, unknown>) =>
    api.get("/sources/images", { params }),
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<{
      url: string;
      thumbnail_url: string;
      storage_key: string;
      width_px: number;
      height_px: number;
      file_size_bytes: number;
      mime_type: string;
    }>("/sources/images/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
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
  list: (params?: Record<string, unknown>) =>
    api.get<ManagedUsersResponse>("/users", { params }),
  create: (data: CreateUserPayload) => api.post<ManagedUser>("/users", data),
  update: (id: string, data: UpdateUserPayload) =>
    api.patch<ManagedUser>(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
};

export const rolesApi = {
  list: () => api.get<RolesResponse>("/roles"),
  create: (data: CreateRolePayload) => api.post<ManagedRole>("/roles", data),
  update: (id: string, data: UpdateRolePayload) =>
    api.patch<ManagedRole>(`/roles/${id}`, data),
  delete: (id: string) => api.delete(`/roles/${id}`),
};
