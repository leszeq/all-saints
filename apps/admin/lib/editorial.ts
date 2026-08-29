export type PublicationStatus = "draft" | "review" | "published" | "archived";
export type EditorialPriority = "urgent" | "high" | "normal";

export interface EditorialIssue {
  code: string;
  label: string;
  severity: "critical" | "warning" | string;
}

export interface EditorialAvatar {
  url: string;
  thumbnail_url?: string | null;
  title?: string | null;
}

export interface EditorialLastEditor {
  id: string;
  full_name: string;
  avatar_url?: string | null;
}

export interface EditorialQueueItem {
  id: string;
  slug: string;
  canonical_name: string;
  person_type: string;
  status: PublicationStatus;
  version: number;
  avatar?: EditorialAvatar | null;
  updated_at: string;
  last_modified_by?: EditorialLastEditor | null;
  age_days: number;
  completeness_score: number;
  completeness_criteria: Array<{
    key: string;
    label: string;
    weight: number;
    completed: boolean;
  }>;
  priority: EditorialPriority;
  issues: EditorialIssue[];
  can_publish: boolean;
}

export interface EditorialQueueCounts {
  total: number;
  draft: number;
  review: number;
  attention: number;
  urgent: number;
  high: number;
  normal: number;
}

export interface EditorialQueueResponse {
  items: EditorialQueueItem[];
  counts: EditorialQueueCounts;
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface EditorialQualitySummary {
  records_with_issues: number;
  total_issues: number;
  duplicate_groups: number;
  duplicate_records: number;
  source_items_to_review: number;
  bibliography_sources: number;
  historical_sources: number;
  person_source_links: number;
  documented_persons: number;
  undocumented_persons: number;
  unknown_license_images: number;
}

export interface EditorialQualityIssueBreakdown {
  code: string;
  label: string;
  severity: "critical" | "warning" | string;
  count: number;
}

export interface EditorialQualityRecord {
  id: string;
  slug: string;
  canonical_name: string;
  person_type: string;
  status: PublicationStatus;
  avatar?: EditorialAvatar | null;
  updated_at: string;
  completeness_score: number;
  source_count: number;
  image_count: number;
  unknown_license_count: number;
  priority: EditorialPriority;
  issues: EditorialIssue[];
}

export interface EditorialDuplicatePerson {
  id: string;
  slug: string;
  canonical_name: string;
  person_type: string;
  status: PublicationStatus;
  birth_year?: number | null;
  death_year?: number | null;
  updated_at: string;
  avatar?: EditorialAvatar | null;
  source_count: number;
  image_count: number;
}

export interface EditorialDuplicateGroup {
  key: string;
  confidence: number;
  reason: string;
  persons: EditorialDuplicatePerson[];
}

export interface EditorialSourceVerificationStats {
  bibliography_sources: number;
  historical_sources: number;
  person_source_links: number;
  documented_persons: number;
  undocumented_persons: number;
  images: number;
  unknown_license_images: number;
}

export interface EditorialSourceVerificationItem {
  id: string;
  item_type: string;
  title: string;
  issue: string;
  severity: "critical" | "warning" | string;
  related_person_id?: string | null;
  related_person_name?: string | null;
  source_url?: string | null;
  updated_at: string;
}

export interface EditorialQualityReport {
  generated_at: string;
  summary: EditorialQualitySummary;
  issue_breakdown: EditorialQualityIssueBreakdown[];
  problem_records: EditorialQualityRecord[];
  duplicate_groups: EditorialDuplicateGroup[];
  source_stats: EditorialSourceVerificationStats;
  source_verification_items: EditorialSourceVerificationItem[];
}

export interface EditorialDashboard {
  generated_at: string;
  total_persons: number;
  status_counts: Array<{ status: PublicationStatus; count: number }>;
  attention_count: number;
  unknown_license_images: number;
  completion: Array<{
    key: string;
    label: string;
    count: number;
    percentage: number;
  }>;
  monthly_activity: Array<{ month: string; count: number }>;
  recent_records: EditorialQueueItem[];
  queue_preview: EditorialQueueItem[];
  queue_counts: EditorialQueueCounts;
  resources: {
    users: number;
    countries: number;
    orders: number;
    bibliography: number;
  };
}

export const EDITORIAL_PRIORITY_LABELS: Record<EditorialPriority, string> = {
  urgent: "Pilny",
  high: "Wysoki",
  normal: "Standardowy",
};

export const EDITORIAL_PRIORITY_COLORS: Record<EditorialPriority, string> = {
  urgent: "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300",
  high: "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  normal: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export function formatEditorialAge(days: number): string {
  if (days <= 0) return "dzisiaj";
  if (days === 1) return "wczoraj";
  return `${days} dni temu`;
}
