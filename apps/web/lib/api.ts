import axios from "axios";
import { DEFAULT_WEB_UI_LOCALE, type WebUiLocale } from "@/lib/i18n/config";

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
  paramsSerializer: {
    serialize: serializeParams,
  },
});

export function isApiNotFound(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

export const fetchPersons = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/persons", {
    params: { locale: DEFAULT_WEB_UI_LOCALE, ...params },
  });
  return data;
};

export const fetchPublicPersonIndex = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/public-index/persons", { params });
  return data;
};

export const fetchPersonDetail = async (
  idOrSlug: string,
  locale: WebUiLocale = DEFAULT_WEB_UI_LOCALE,
) => {
  const { data } = await publicApi.get(`/persons/${idOrSlug}`, { params: { locale } });
  return data;
};

export const fetchCountries = async () => {
  const { data } = await publicApi.get("/geography/countries");
  return data;
};

export const fetchOrders = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/orders", { params });
  return data;
};

export const fetchOrderDetail = async (idOrSlug: string) => {
  const { data } = await publicApi.get(`/orders/${idOrSlug}`);
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
  const { data } = await publicApi.get(`/calendar/observances/by-slug/${slug}`);
  return data;
};
