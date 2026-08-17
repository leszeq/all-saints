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

export const fetchOrders = async () => {
  const { data } = await publicApi.get("/orders");
  return data;
};

export const fetchCategories = async () => {
  const { data } = await publicApi.get("/taxonomy/categories");
  return data;
};
