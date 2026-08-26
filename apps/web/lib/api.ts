import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const publicApi = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

export const fetchPersons = async (params?: Record<string, unknown>) => {
  const { data } = await publicApi.get("/persons", { params });
  return data;
};

export const fetchPersonDetail = async (idOrSlug: string) => {
  const { data } = await publicApi.get(`/persons/${idOrSlug}`);
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
