import type { SaintAvatarData } from "@/components/saint-avatar";

export interface ReligiousOrder {
  id: string;
  slug: string;
  name: string;
  name_la?: string | null;
  name_local?: string | null;
  abbreviation?: string | null;
  community_type: string;
  spiritual_family?: string | null;
  founded_year?: number | null;
  founder_id?: string | null;
  founder_name?: string | null;
  papal_approval_year?: number | null;
  charism?: string | null;
  description?: string | null;
  history?: string | null;
  mission?: string | null;
  motto?: string | null;
  website_url?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  is_featured: boolean;
  member_count: number;
  sort_order: number;
}

export interface OrderMember {
  entry_date?: string | null;
  exit_date?: string | null;
  is_founder: boolean;
  membership_type: string;
  notes?: string | null;
  person: {
    id: string;
    slug: string;
    canonical_name: string;
    person_type: string;
    birth_year?: number | null;
    death_year?: number | null;
    summary_pl?: string | null;
    avatar?: SaintAvatarData | null;
  };
}

export interface ReligiousOrderDetail extends ReligiousOrder {
  members: OrderMember[];
}

export function orderMonogram(order: Pick<ReligiousOrder, "abbreviation" | "name">): string {
  if (order.abbreviation) return order.abbreviation;
  return order.name
    .split(/\s+/)
    .filter((word) => word.length > 2)
    .slice(0, 3)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function formatOrderMemberCount(count: number): string {
  if (count === 1) return "1 powiązana postać";
  const lastTwoDigits = count % 100;
  const lastDigit = count % 10;
  if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwoDigits >= 12 && lastTwoDigits <= 14)) {
    return `${count} powiązane postacie`;
  }
  return `${count} powiązanych postaci`;
}
