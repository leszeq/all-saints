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

export interface ProductEventAggregate {
  day: string;
  event_name: ProductEventName;
  query_class: ProductQueryClass | null;
  event_count: number;
  unique_sessions: number;
  result_count_sum: number;
  zero_results_count: number;
  search_success_count: number;
  generated_at: string;
}

export interface ProductEventAggregatesResponse {
  start_date: string;
  end_date: string;
  generated_at: string;
  items: ProductEventAggregate[];
}
