export type CommunityType =
  | "religious_order"
  | "congregation"
  | "monastic_family"
  | "society_apostolic_life"
  | "secular_institute"
  | "federation"
  | "other";

export type OrderCharism =
  | "contemplative"
  | "apostolic"
  | "mendicant"
  | "monastic"
  | "missionary"
  | "educational"
  | "charitable"
  | "military"
  | "other";

export type OrderMembershipType =
  | "founder"
  | "monk"
  | "friar"
  | "nun"
  | "sister"
  | "lay_member"
  | "spiritual_patron"
  | "member";

export interface ReligiousOrder {
  id: string;
  slug: string;
  name: string;
  name_la: string | null;
  name_local: string | null;
  abbreviation: string | null;
  community_type: CommunityType;
  spiritual_family: string | null;
  founded_year: number | null;
  founded_place_id: string | null;
  founder_id: string | null;
  founder_name: string | null;
  suppressed_year: number | null;
  charism: OrderCharism | null;
  description: string | null;
  description_en: string | null;
  history: string | null;
  mission: string | null;
  motto: string | null;
  website_url: string | null;
  source_title: string | null;
  source_url: string | null;
  papal_approval_year: number | null;
  is_suppressed: boolean;
  is_featured: boolean;
  sort_order: number;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface ReligiousOrderPayload {
  slug: string;
  name: string;
  name_la: string | null;
  name_local: string | null;
  abbreviation: string | null;
  community_type: CommunityType;
  spiritual_family: string | null;
  founded_year: number | null;
  founder_name: string | null;
  suppressed_year: number | null;
  charism: OrderCharism | null;
  description: string | null;
  description_en: string | null;
  history: string | null;
  mission: string | null;
  motto: string | null;
  website_url: string | null;
  source_title: string | null;
  source_url: string | null;
  papal_approval_year: number | null;
  is_suppressed: boolean;
  is_featured: boolean;
  sort_order: number;
}

export interface PersonOrderMembership {
  entry_date: string | null;
  exit_date: string | null;
  is_founder: boolean;
  membership_type: OrderMembershipType;
  notes: string | null;
  order: Pick<
    ReligiousOrder,
    "id" | "slug" | "name" | "abbreviation" | "community_type" | "spiritual_family"
  >;
}

export interface CreateOrderMembershipPayload {
  person_id: string;
  entry_date?: string | null;
  exit_date?: string | null;
  is_founder: boolean;
  membership_type: OrderMembershipType;
  notes?: string | null;
}

