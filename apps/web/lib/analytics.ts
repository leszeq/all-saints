import { publicApi } from "@/lib/api";

export type ProductEventName =
  | "search_submitted"
  | "search_results"
  | "profile_opened"
  | "source_opened"
  | "relation_opened"
  | "filter_applied"
  | "feedback_submitted";

export type ProductQueryClass =
  | "name"
  | "patronage"
  | "occupation"
  | "order"
  | "country"
  | "period"
  | "filter";

export type ProductFilterName =
  | "person_type"
  | "gender"
  | "period"
  | "patronage"
  | "order"
  | "occupation"
  | "birth_country"
  | "death_country"
  | "nationality";

export type ProductSourceKind = "bibliography" | "historical" | "image" | "web";

export type ProductRelationKind = "order" | "patronage" | "occupation" | "geography" | "calendar";

export type ProductFeedback = "helpful" | "not_helpful";

export type ProductEventProperties = {
  result_count?: number;
  filter_name?: ProductFilterName;
  source_kind?: ProductSourceKind;
  relation_kind?: ProductRelationKind;
  feedback?: ProductFeedback;
};

type ProductEventDetails = {
  query_class?: ProductQueryClass;
  properties?: ProductEventProperties;
};

const SESSION_STORAGE_KEY = "saints:analytics-session";

function createSessionId(): string | null {
  try {
    if (typeof crypto.randomUUID === "function") return crypto.randomUUID();

    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  } catch {
    return null;
  }
}

export function getProductAnalyticsSessionId(): string | null {
  if (typeof window === "undefined") return null;

  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;

    const sessionId = createSessionId();
    if (sessionId) window.sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    return sessionId;
  } catch {
    return null;
  }
}

export function recordProductEvent(
  eventName: ProductEventName,
  details: ProductEventDetails = {},
): void {
  if (typeof window === "undefined") return;

  const sessionId = getProductAnalyticsSessionId();
  if (!sessionId) return;

  const body = JSON.stringify({
    event_name: eventName,
    session_id: sessionId,
    ...details,
  });
  const endpoint = `${publicApi.defaults.baseURL ?? ""}/events`;

  try {
    if (typeof navigator.sendBeacon === "function") {
      const accepted = navigator.sendBeacon(
        endpoint,
        new Blob([body], { type: "application/json" }),
      );
      if (accepted) return;
    }
  } catch {
    // The fetch fallback keeps instrumentation non-blocking.
  }

  void fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => undefined);
}
