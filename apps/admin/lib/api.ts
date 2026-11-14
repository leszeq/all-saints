// Centralny klient HTTP dla wszystkich wywołań API
import axios from "axios";
import type {
  AiDashboard,
  AiSuggestionDecisionPayload,
  AiSuggestionDecisionResponse,
  AiSuggestionsResponse,
} from "@/lib/ai";
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
import type { ProductEventAggregatesResponse } from "@/lib/analytics";
import type {
  CreateOrderMembershipPayload,
  ReligiousOrder,
  ReligiousOrderImportDocument,
  ReligiousOrderImportValidationResult,
  ReligiousOrderPayload,
} from "@/lib/orders";
import { useAuthStore } from "@/lib/store/auth";
import type {
  ConceptAlias,
  ConceptAliasPayload,
  PatronageConcept,
  PatronageConceptPayload,
  PatronageConceptReviewPayload,
} from "@/lib/taxonomy";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_REQUEST_TIMEOUT_MS = 60_000;
const REFRESH_REQUEST_TIMEOUT_MS = 15_000;

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  withCredentials: true, // HttpOnly refresh cookie
  timeout: API_REQUEST_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
});

interface ApiErrorPayload {
  error?: string;
  detail?: string | { message?: string; errors?: unknown[] } | Array<unknown>;
  message?: string;
  details?: unknown[];
  request_id?: string | null;
}

export interface ApiErrorDetail {
  code?: string;
  field?: string;
  message?: string;
  severity?: string;
  type?: string;
}

export interface ApiConflictDetails {
  code?: string;
  expectedVersion?: number;
  currentVersion?: number;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

let refreshPromise: Promise<string> | null = null;

export interface ApiErrorMessageOptions {
  messagesByCode?: Readonly<Record<string, string>>;
  unexpected: string;
  invalidValue: string;
  invalidData: string;
  network: string;
  httpError: (status: number) => string;
}

async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post<TokenResponse>(
        `${API_BASE_URL}/api/v1/auth/refresh`,
        {},
        { withCredentials: true, timeout: REFRESH_REQUEST_TIMEOUT_MS },
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

export function getApiErrorMessage(
  error: unknown,
  options: ApiErrorMessageOptions,
): string {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) {
    return options.unexpected;
  }

  const payload = error.response?.data;
  const localizedCodeMessage = payload?.error
    ? options.messagesByCode?.[payload.error]
    : undefined;
  if (payload?.details?.length) {
    const structuredMessage = payload.details
      .map((value) => {
        const detail = normalizeApiErrorDetail(value);
        if (!detail) return null;
        const fieldName = detail.field ? formatApiErrorField(detail.field) : undefined;
        return fieldName
          ? `${fieldName}: ${detail.message ?? options.invalidValue}`
          : detail.message;
      })
      .filter((message): message is string => Boolean(message))
      .join(" · ");
    if (structuredMessage) {
      return [localizedCodeMessage, structuredMessage].filter(Boolean).join(" · ");
    }
  }

  if (localizedCodeMessage) return localizedCodeMessage;

  if (payload?.message) return payload.message;
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    const validationMessages = payload.detail
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const entry = item as { loc?: Array<string | number>; msg?: string };
        if (!entry.msg) return null;
        const field = entry.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${entry.msg}` : entry.msg;
      })
      .filter((item): item is string => Boolean(item));
    if (validationMessages.length) return validationMessages.join(" · ");
  }
  if (payload?.detail && !Array.isArray(payload.detail) && typeof payload.detail === "object") {
    const detailMessage = payload.detail.message;
    const detailErrors = payload.detail.errors;
    return (
      [detailMessage, ...(detailErrors ?? [])].filter(Boolean).join(" · ") ||
      options.invalidData
    );
  }
  if (!error.response) {
    return options.network;
  }
  return options.httpError(error.response.status);
}

function normalizeApiErrorDetail(value: unknown): ApiErrorDetail | null {
  if (typeof value === "string" && value) return { message: value };
  if (!value || typeof value !== "object") return null;

  const entry = value as {
    code?: unknown;
    field?: unknown;
    loc?: unknown;
    label?: unknown;
    message?: unknown;
    msg?: unknown;
    severity?: unknown;
    type?: unknown;
  };
  const location = Array.isArray(entry.loc)
    ? entry.loc.map((part) => String(part)).join(".")
    : undefined;
  const field = typeof entry.field === "string" ? entry.field : location;
  const message = typeof entry.message === "string"
    ? entry.message
    : typeof entry.msg === "string"
      ? entry.msg
      : typeof entry.label === "string"
        ? entry.label
      : undefined;
  const type = typeof entry.type === "string"
    ? entry.type
    : typeof entry.code === "string"
      ? entry.code
      : undefined;
  const severity = typeof entry.severity === "string" ? entry.severity : undefined;

  if (!field && !message && !type) return null;
  return { code: typeof entry.code === "string" ? entry.code : undefined, field, message, severity, type };
}

/** Extract structured validation entries without exposing Axios internals to UI components. */
export function getApiErrorDetails(error: unknown): ApiErrorDetail[] {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) return [];
  const payload = error.response?.data;
  if (!payload) return [];

  let rawDetails: unknown[] = [];
  if (Array.isArray(payload.details)) {
    rawDetails = payload.details;
  } else if (Array.isArray(payload.detail)) {
    rawDetails = payload.detail;
  } else if (
    payload.detail &&
    typeof payload.detail === "object" &&
    !Array.isArray(payload.detail) &&
    Array.isArray(payload.detail.errors)
  ) {
    rawDetails = payload.detail.errors;
  }

  return rawDetails
    .map(normalizeApiErrorDetail)
    .filter((detail): detail is ApiErrorDetail => detail !== null);
}

/** Read optimistic-lock metadata from a 409 response without coupling UI to Axios. */
export function getApiConflictDetails(error: unknown): ApiConflictDetails | null {
  if (!axios.isAxiosError<ApiErrorPayload>(error) || error.response?.status !== 409) {
    return null;
  }

  const payload = error.response.data;
  const detail = payload?.detail && typeof payload.detail === "object" && !Array.isArray(payload.detail)
    ? payload.detail as Record<string, unknown>
    : null;
  const source = detail ?? (payload as Record<string, unknown> | undefined);
  if (!source) return null;

  const asVersion = (value: unknown) => {
    const version = Number(value);
    return Number.isInteger(version) && version > 0 ? version : undefined;
  };

  const code = typeof source.code === "string" ? source.code : undefined;
  const expectedVersion = asVersion(source.expected_version);
  const currentVersion = asVersion(source.current_version);
  if (!code && expectedVersion === undefined && currentVersion === undefined) return null;
  return { code, expectedVersion, currentVersion };
}

/** Turn Pydantic's dotted location into a path a person can find in the JSON file. */
export function formatApiErrorField(field: string): string {
  return field
    .replace(/^(body|query|path)\./, "")
    .split(".")
    .reduce((formatted, part) => {
      if (/^\d+$/.test(part)) return `${formatted}[${part}]`;
      return formatted ? `${formatted}.${part}` : part;
    }, "");
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
  versions: (id: string, params?: { page?: number; per_page?: number }) =>
    api.get(`/persons/${id}/versions`, { params }),
  exportProfile: (id: string) => api.get(`/persons/admin/${id}/export`),
  validateProfileImport: (data: unknown, params?: { overwrite_person_id: string; expected_version: number }) =>
    api.post("/persons/import/validate", data, { params }),
  importProfile: (data: unknown, params?: { overwrite_person_id: string; expected_version: number }) =>
    api.post("/persons/import", data, { params }),
  activeRevision: (personId: string) =>
    api.get<PublicationRevision | null>(`/persons/${personId}/revisions/active`),
  createRevision: (
    personId: string,
    data: { expected_version: number; change_summary?: string | null },
  ) => api.post<PublicationRevision>(`/persons/${personId}/revisions`, data),
};

export type PublicationRevisionStatus = "draft" | "review" | "published" | "rejected";

export interface PublicationRevision {
  id: string;
  person_id: string;
  revision_number: number;
  status: PublicationRevisionStatus;
  base_version: number;
  base_revision_id: string | null;
  payload: Record<string, unknown>;
  author_id: string | null;
  change_summary: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export const publicationRevisionsApi = {
  update: (
    revisionId: string,
    data: {
      expected_version: number;
      changes: Record<string, unknown>;
      change_summary?: string | null;
    },
  ) => api.patch<PublicationRevision>(`/revisions/${revisionId}`, data),
  submit: (
    revisionId: string,
    data: { expected_version: number; note?: string | null },
  ) => api.post<PublicationRevision>(`/revisions/${revisionId}/submit`, data),
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
  decideSuggestion: (
    kind: "summary" | "tags",
    personId: string,
    data: AiSuggestionDecisionPayload,
  ) =>
    api.post<AiSuggestionDecisionResponse>(
      `/ai/suggestions/${kind}/${personId}/decision`,
      data,
    ),
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
  list: (params?: Record<string, unknown>) =>
    api.get<ReligiousOrder[]>("/orders", { params }),
  management: (params?: Record<string, unknown>) =>
    api.get<ReligiousOrder[]>("/orders/management", { params }),
  create: (data: ReligiousOrderPayload) => api.post<ReligiousOrder>("/orders", data),
  validateImport: (data: ReligiousOrderImportDocument) =>
    api.post<ReligiousOrderImportValidationResult>("/orders/import/validate", data),
  importBatch: (data: ReligiousOrderImportDocument) =>
    api.post<ReligiousOrder[]>("/orders/import", data),
  update: (idOrSlug: string, data: ReligiousOrderPayload) =>
    api.patch<ReligiousOrder>(`/orders/${idOrSlug}`, data),
  delete: (idOrSlug: string) => api.delete(`/orders/${idOrSlug}`),
  addMember: (idOrSlug: string, data: CreateOrderMembershipPayload) =>
    api.post(`/orders/${idOrSlug}/members`, data),
  removeMember: (idOrSlug: string, personId: string) =>
    api.delete(`/orders/${idOrSlug}/members/${personId}`),
};

export const popesApi = {
  list: (params?: Record<string, unknown>) => api.get("/popes", { params }),
  create: (data: unknown) => api.post("/popes", data),
};

export const sourcesApi = {
  bibliography: (params?: Record<string, unknown>) =>
    api.get("/sources/bibliography", { params }),
  updateBibliography: (id: string, data: unknown) =>
    api.patch(`/sources/bibliography/${id}`, data),
  historicalSources: (params?: Record<string, unknown>) =>
    api.get("/sources/historical-sources", { params }),
  updateHistoricalSource: (id: string, data: unknown) =>
    api.patch(`/sources/historical-sources/${id}`, data),
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
  occupations: (params?: Record<string, unknown>) =>
    api.get("/taxonomy/occupations", { params }),
  patronages: (params?: Record<string, unknown>) =>
    api.get<PatronageConcept[]>("/taxonomy/patronages/management", { params }),
  createPatronage: (data: PatronageConceptPayload) =>
    api.post<PatronageConcept>("/taxonomy/patronages", data),
  updatePatronage: (id: string, data: Partial<PatronageConceptPayload>) =>
    api.patch<PatronageConcept>(`/taxonomy/patronages/${id}`, data),
  addPatronageAlias: (id: string, data: ConceptAliasPayload) =>
    api.post<ConceptAlias>(`/taxonomy/patronages/${id}/aliases`, data),
  submitPatronage: (id: string) =>
    api.post<PatronageConcept>(`/taxonomy/patronages/${id}/submit`, {
      target_status: "review",
    } satisfies PatronageConceptReviewPayload),
  reviewPatronage: (id: string, data: PatronageConceptReviewPayload) =>
    api.post<PatronageConcept>(`/taxonomy/patronages/${id}/review`, data),
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

export const analyticsApi = {
  rebuild: (params?: { start_date?: string; end_date?: string }) =>
    api.post<ProductEventAggregatesResponse>("/events/aggregates/rebuild", undefined, { params }),
  aggregates: (params?: { start_date?: string; end_date?: string }) =>
    api.get<ProductEventAggregatesResponse>("/events/aggregates", { params }),
};
