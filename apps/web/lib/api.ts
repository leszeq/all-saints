import axios from "axios";
import { DEFAULT_WEB_UI_LOCALE, type WebUiLocale } from "@/lib/i18n/config";

const PUBLIC_READ_TIMEOUT_MS = 10_000;
const PUBLIC_READ_RETRY_DELAY_MS = 150;

const API_BASE_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const serializeParams = (params: Record<string, unknown>) => {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      if (item === undefined || item === null || item === "") return;
      searchParams.append(key, String(item));
    });
  });

  return searchParams.toString();
};

export const publicApi = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: PUBLIC_READ_TIMEOUT_MS,
  paramsSerializer: {
    serialize: serializeParams,
  },
});

function isTransientPublicReadError(error: unknown): boolean {
  if (!axios.isAxiosError(error) || error.response || axios.isCancel(error)) return false;
  return new Set(["ECONNABORTED", "ECONNRESET", "ETIMEDOUT", "ERR_NETWORK"]).has(
    error.code ?? "",
  );
}

async function waitForPublicReadRetry(attempt: number): Promise<void> {
  await new Promise((resolve) =>
    setTimeout(resolve, PUBLIC_READ_RETRY_DELAY_MS * 2 ** attempt),
  );
}

export function isApiNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

export const fetchPersons = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/persons", {
    params: { locale: DEFAULT_WEB_UI_LOCALE, ...params },
  });
  return data;
};

export const fetchPersonFacets = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/persons/facets", { params });
  return data;
};

export const fetchPublicPersonIndex = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/public-index/persons", { params });
  return data;
};

export const fetchPersonDetail = async (
  idOrSlug: string,
  locale: WebUiLocale = DEFAULT_WEB_UI_LOCALE,
  params?: { sources_page?: number; sources_per_page?: number },
) => {
  const { data } = await publicApi.get(`/persons/${idOrSlug}`, {
    params: { locale, ...params },
  });
  return data;
};

export const fetchPersonCommemorations = async (idOrSlug: string) => {
  const { data } = await publicApi.get(`/persons/${idOrSlug}/commemorations`);
  return data;
};

export const fetchCountries = async () => {
  const { data } = await publicApi.get("/geography/countries");
  return data;
};

export const fetchOccupations = async () => {
  const { data } = await publicApi.get("/taxonomy/occupations");
  return data;
};

export const fetchPatronages = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/taxonomy/patronages", { params });
  return data;
};

export const fetchPatronagePersons = async (slug: string, params?: Record<string, unknown>) => {
  const { data } = await publicApi.get(`/taxonomy/patronages/${encodeURIComponent(slug)}/persons`, {
    params,
  });
  return data;
};

export const fetchOrders = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/orders", { params });
  return data;
};

export const fetchOrderDetail = async (
  idOrSlug: string,
  params?: { members_page?: number; members_per_page?: number },
) => {
  const { data } = await publicApi.get(`/orders/${encodeURIComponent(idOrSlug)}`, { params });
  return data;
};

export const fetchCategories = async () => {
  const { data } = await publicApi.get("/taxonomy/categories");
  return data;
};

export const fetchSourceStats = async () => {
  const { data } = await publicApi.get("/sources/stats");
  return data;
};

export const fetchCalendarToday = async (calendarCode = "roman_pl") => {
  const { data } = await publicApi.get("/calendar/today", {
    params: {
      calendar_code: calendarCode,
      include_universal: true,
      include_martyrology: true,
    },
  });
  return data;
};

export const fetchCalendarDay = async (date: string, calendarCode = "roman_pl") => {
  const { data } = await publicApi.get(`/calendar/day/${date}`, {
    params: {
      calendar_code: calendarCode,
      include_universal: true,
      include_martyrology: true,
    },
  });
  return data;
};

export const fetchCalendarMonth = async (
  year: number,
  month: number,
  calendarCode = "roman_pl",
) => {
  const { data } = await publicApi.get(`/calendar/month/${year}/${month}`, {
    params: {
      calendar_code: calendarCode,
      include_universal: true,
      include_martyrology: true,
    },
  });
  return data;
};

export const fetchLiturgicalCalendars = async () => {
  const { data } = await publicApi.get("/calendar/calendars");
  return data;
};

export const fetchLiturgicalObservance = async (slug: string) => {
  const path = `/calendar/observances/by-slug/${encodeURIComponent(slug)}`;
  for (let attempt = 0; ; attempt += 1) {
    try {
      const { data } = await publicApi.get(path);
      return data;
    } catch (error) {
      if (attempt >= 1 || !isTransientPublicReadError(error)) throw error;
      await waitForPublicReadRetry(attempt);
    }
  }
};
