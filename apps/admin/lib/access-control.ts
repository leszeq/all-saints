export type UserStatus = "active" | "inactive" | "banned" | "pending_verification";

export interface ManagedRoleSummary {
  id: string;
  name: string;
  display_name: string;
  is_system: boolean;
}

export interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  status: UserStatus;
  roles: string[];
  primary_role: ManagedRoleSummary | null;
  created_at: string;
  last_login_at: string | null;
}

export interface ManagedUsersResponse {
  items: ManagedUser[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface PermissionDefinition {
  key: string;
  resource: string;
  action: string;
  description: string;
  group: string;
  assignable_to_custom_roles: boolean;
}

export interface ManagedRole {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_system: boolean;
  user_count: number;
  permissions: string[];
  created_at: string;
}

export interface RolesResponse {
  items: ManagedRole[];
  permissions: PermissionDefinition[];
}

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name: string;
  role_id: string;
  preferred_language?: string;
}

export interface UpdateUserPayload {
  full_name?: string;
  status?: UserStatus;
  role_id?: string;
  preferred_language?: string;
  bio?: string;
}

export interface CreateRolePayload {
  name: string;
  display_name: string;
  description?: string;
  permissions: string[];
}

export interface UpdateRolePayload {
  display_name?: string;
  description?: string;
  permissions?: string[];
}

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Superadministrator",
  admin: "Administrator",
  editor: "Redaktor",
  reviewer: "Recenzent",
  translator: "Tłumacz",
  reader: "Czytelnik wewnętrzny",
  guest: "Gość",
};

export const USER_STATUS_LABELS: Record<UserStatus, string> = {
  active: "Aktywny",
  inactive: "Nieaktywny",
  banned: "Zablokowany",
  pending_verification: "Oczekuje na aktywację",
};

export const USER_STATUS_COLORS: Record<UserStatus, string> = {
  active: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  inactive: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  banned: "bg-rose-100 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300",
  pending_verification: "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
};
