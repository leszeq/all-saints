export type AiSuggestionKind = "embedding" | "summary" | "tags";
export type AiSuggestionStatus = "pending_review" | "ready_to_generate" | "blocked";

export interface AiSuggestionItem {
  id: string;
  person_id: string;
  person_slug: string;
  person_name: string;
  kind: AiSuggestionKind;
  status: AiSuggestionStatus;
  title: string;
  description: string;
  current_value?: string | null;
  suggested_value?: string | null;
  confidence: number;
  reason: string;
  action: "generate_embedding" | "generate_summary" | "generate_tags" | "review_person" | string;
  action_href: string;
  updated_at: string;
}

export interface AiSuggestionsResponse {
  items: AiSuggestionItem[];
  total: number;
  pending_review: number;
  ready_to_generate: number;
  blocked: number;
}

export interface AiFeatureStatus {
  key: string;
  label: string;
  status: "ready" | "disabled" | "needs_data" | "fallback" | string;
  description: string;
  detail: string;
}

export interface AiDashboard {
  generated_at: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  summary_provider: string;
  total_persons: number;
  published_persons: number;
  total_embeddings: number;
  missing_embeddings: number;
  coverage_percent: number;
  ai_summaries: number;
  ai_tags: number;
  pending_suggestions: number;
  blocked_suggestions: number;
  last_generated_at?: string | null;
  feature_statuses: AiFeatureStatus[];
  recent_suggestions: AiSuggestionItem[];
}

export const AI_SUGGESTION_STATUS_COLORS: Record<AiSuggestionStatus, string> = {
  pending_review: "bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
  ready_to_generate: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  blocked: "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300",
};

export const AI_FEATURE_STATUS_COLORS: Record<string, string> = {
  ready: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  disabled: "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300",
  needs_data: "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  fallback: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};
