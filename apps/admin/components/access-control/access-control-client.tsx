"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type {
  CreateRolePayload,
  CreateUserPayload,
  ManagedRole,
  ManagedUser,
  PermissionDefinition,
  UpdateRolePayload,
  UpdateUserPayload,
  UserStatus,
} from "@/lib/access-control";
import { USER_STATUS_COLORS } from "@/lib/access-control";
import { getApiErrorMessage, rolesApi, usersApi } from "@/lib/api";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminAccessControlDictionary,
  AdminPermissionGroupKey,
  AdminPermissionKey,
  AdminSystemRoleKey,
  AdminTopbarDictionary,
} from "@/lib/i18n/types";
import { useAuthStore } from "@/lib/store/auth";
import { cn } from "@/lib/utils";

type ActiveTab = "users" | "matrix";

const inputClassName =
  "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15";

type PermissionGroup = {
  key: string;
  label: string;
  permissions: PermissionDefinition[];
};

const PERMISSION_GROUP_BY_RESOURCE: Readonly<Record<string, AdminPermissionGroupKey>> = {
  sources: "sources_media",
  images: "sources_media",
  geography: "geography",
  orders: "orders",
  calendar: "calendar",
  translations: "translations",
  export: "import_export",
  import: "import_export",
  audit: "administration",
  users: "administration",
  roles: "administration",
};

function getPermissionGroupKey(permission: PermissionDefinition): AdminPermissionGroupKey | null {
  if (permission.resource === "persons") {
    return ["submit", "review", "publish"].includes(permission.action)
      ? "editorial_workflow"
      : "persons";
  }
  return PERMISSION_GROUP_BY_RESOURCE[permission.resource] ?? null;
}

function groupPermissions(
  permissions: PermissionDefinition[],
  copy: AdminAccessControlDictionary,
): PermissionGroup[] {
  const groups = new Map<string, PermissionGroup>();
  permissions.forEach((permission) => {
    const stableKey = getPermissionGroupKey(permission);
    const key = stableKey ?? `fallback:${permission.group}`;
    const existing = groups.get(key);
    if (existing) {
      existing.permissions.push(permission);
      return;
    }
    groups.set(key, {
      key,
      label: stableKey ? copy.permissionGroupLabels[stableKey] : permission.group,
      permissions: [permission],
    });
  });
  return Array.from(groups.values());
}

function getPermissionLabel(
  permission: PermissionDefinition,
  copy: AdminAccessControlDictionary,
): string {
  return permission.key in copy.permissionLabels
    ? copy.permissionLabels[permission.key as AdminPermissionKey]
    : permission.description;
}

function getSystemRoleLabel(
  roleName: string,
  roleLabels: AdminTopbarDictionary["roleLabels"],
  fallback: string,
): string {
  return roleName in roleLabels
    ? roleLabels[roleName as AdminSystemRoleKey]
    : fallback;
}

function getSystemRoleDescription(
  role: ManagedRole,
  copy: AdminAccessControlDictionary,
): string {
  if (role.is_system && role.name in copy.roles.systemDescriptions) {
    return copy.roles.systemDescriptions[role.name as AdminSystemRoleKey];
  }
  return role.description || copy.roles.noDescription;
}

function ModalShell({
  open,
  onOpenChange,
  title,
  description,
  closeAriaLabel,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  closeAriaLabel: string;
  children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/55 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl focus:outline-none">
          <div className="pr-10">
            <Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm leading-6 text-muted-foreground">
              {description}
            </Dialog.Description>
          </div>
          <Dialog.Close className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={closeAriaLabel}>
            <X className="h-4 w-4" />
          </Dialog.Close>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ErrorMessage({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {message}
    </div>
  );
}

function UserForm({
  user,
  roles,
  pending,
  error,
  copy,
  roleLabels,
  onSubmit,
  onCancel,
}: {
  user: ManagedUser | null;
  roles: ManagedRole[];
  pending: boolean;
  error: string;
  copy: AdminAccessControlDictionary;
  roleLabels: AdminTopbarDictionary["roleLabels"];
  onSubmit: (payload: CreateUserPayload | UpdateUserPayload) => void;
  onCancel: () => void;
}) {
  const selectableRoles = roles.filter((role) => role.name !== "super_admin");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const common = {
      full_name: String(form.get("full_name") ?? "").trim(),
      role_id: String(form.get("role_id") ?? ""),
    };
    if (user) {
      onSubmit({
        ...common,
        status: String(form.get("status") ?? "active") as UserStatus,
      });
      return;
    }
    onSubmit({
      ...common,
      email: String(form.get("email") ?? "").trim(),
      password: String(form.get("password") ?? ""),
      preferred_language: "pl",
    });
  };

  return (
    <form onSubmit={handleSubmit} className="mt-6 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1.5 text-sm font-medium">
          {copy.userDialog.fullName}
          <input name="full_name" defaultValue={user?.full_name ?? ""} required minLength={2} maxLength={300} className={inputClassName} />
        </label>
        <label className="space-y-1.5 text-sm font-medium">
          {copy.userDialog.role}
          <select name="role_id" defaultValue={user?.primary_role?.id ?? ""} required className={inputClassName}>
            <option value="" disabled>{copy.userDialog.chooseRole}</option>
            {selectableRoles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.is_system
                  ? getSystemRoleLabel(role.name, roleLabels, role.display_name)
                  : role.display_name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {!user && (
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1.5 text-sm font-medium">
            {copy.userDialog.email}
            <input name="email" type="email" required autoComplete="off" className={inputClassName} />
          </label>
          <label className="space-y-1.5 text-sm font-medium">
            {copy.userDialog.temporaryPassword}
            <input name="password" type="password" required minLength={8} maxLength={128} autoComplete="new-password" className={inputClassName} />
            <span className="block text-[11px] font-normal text-muted-foreground">{copy.userDialog.passwordHelp}</span>
          </label>
        </div>
      )}
      {user && (
        <label className="block space-y-1.5 text-sm font-medium sm:max-w-[calc(50%-0.5rem)]">
          {copy.userDialog.status}
          <select name="status" defaultValue={user.status} className={inputClassName}>
            {Object.entries(copy.userStatusLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
      )}
      <ErrorMessage message={error} />
      <div className="flex justify-end gap-2 border-t border-border pt-4">
        <button type="button" onClick={onCancel} className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">{copy.userDialog.cancelAction}</button>
        <button type="submit" disabled={pending} className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          {pending && <Loader2 className="h-4 w-4 animate-spin" />}
          {user ? copy.userDialog.saveAction : copy.userDialog.createAction}
        </button>
      </div>
    </form>
  );
}

function RoleForm({
  role,
  permissions,
  pending,
  error,
  copy,
  onSubmit,
  onCancel,
}: {
  role: ManagedRole | null;
  permissions: PermissionDefinition[];
  pending: boolean;
  error: string;
  copy: AdminAccessControlDictionary;
  onSubmit: (payload: CreateRolePayload | UpdateRolePayload) => void;
  onCancel: () => void;
}) {
  const assignable = permissions.filter((permission) => permission.assignable_to_custom_roles);
  const groups = useMemo(() => groupPermissions(assignable, copy), [assignable, copy]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = {
      display_name: String(form.get("display_name") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      permissions: form.getAll("permissions").map(String),
    };
    if (role) {
      onSubmit(payload);
      return;
    }
    onSubmit({ ...payload, name: String(form.get("name") ?? "").trim() });
  };

  return (
    <form onSubmit={handleSubmit} className="mt-6 space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        {!role && (
          <label className="space-y-1.5 text-sm font-medium">
            {copy.roleDialog.identifier}
            <input name="name" required minLength={3} maxLength={50} pattern="[a-z][a-z0-9_]+" placeholder={copy.roleDialog.identifierPlaceholder} className={inputClassName} />
            <span className="block text-[11px] font-normal text-muted-foreground">{copy.roleDialog.identifierHelp}</span>
          </label>
        )}
        <label className="space-y-1.5 text-sm font-medium">
          {copy.roleDialog.displayName}
          <input name="display_name" defaultValue={role?.display_name ?? ""} required minLength={2} maxLength={200} className={inputClassName} />
        </label>
      </div>
      <label className="block space-y-1.5 text-sm font-medium">
        {copy.roleDialog.responsibility}
        <textarea name="description" defaultValue={role?.description ?? ""} rows={2} maxLength={1000} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" />
      </label>
      <fieldset>
        <legend className="text-sm font-semibold">{copy.roleDialog.permissionsLegend}</legend>
        <p className="mt-1 text-xs text-muted-foreground">{copy.roleDialog.permissionsHelp}</p>
        <div className="mt-3 max-h-72 space-y-4 overflow-y-auto rounded-lg border border-border p-4">
          {groups.map((group) => (
            <div key={group.key}>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{group.label}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {group.permissions.map((permission) => (
                  <label key={permission.key} className="flex cursor-pointer items-start gap-2 rounded-md p-2 text-xs hover:bg-muted/60">
                    <input type="checkbox" name="permissions" value={permission.key} defaultChecked={role?.permissions.includes(permission.key)} className="mt-0.5 h-4 w-4 accent-primary" />
                    <span><span className="block font-medium text-foreground">{getPermissionLabel(permission, copy)}</span><span className="text-[10px] text-muted-foreground">{permission.key}</span></span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </fieldset>
      <ErrorMessage message={error} />
      <div className="flex justify-end gap-2 border-t border-border pt-4">
        <button type="button" onClick={onCancel} className="h-10 rounded-lg border border-border px-4 text-sm font-medium hover:bg-muted">{copy.roleDialog.cancelAction}</button>
        <button type="submit" disabled={pending} className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          {pending && <Loader2 className="h-4 w-4 animate-spin" />}
          {role ? copy.roleDialog.saveAction : copy.roleDialog.createAction}
        </button>
      </div>
    </form>
  );
}

export function AccessControlClient({
  copy,
  locale,
  roleLabels,
}: {
  copy: AdminAccessControlDictionary;
  locale: string;
  roleLabels: AdminTopbarDictionary["roleLabels"];
}) {
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((state) => state.user);
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const sessionReady = currentUser !== null;
  const [activeTab, setActiveTab] = useState<ActiveTab>("users");
  const [search, setSearch] = useState("");
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [editedUser, setEditedUser] = useState<ManagedUser | null>(null);
  const [editedRole, setEditedRole] = useState<ManagedRole | null>(null);
  const [actionError, setActionError] = useState("");
  const numberFormatter = useMemo(() => new Intl.NumberFormat(locale), [locale]);

  const formatActionError = (error: unknown) =>
    getApiErrorMessage(error, {
      messagesByCode: {
        UNAUTHORIZED: copy.errors.unauthorized,
        FORBIDDEN: copy.errors.forbidden,
        NOT_FOUND: copy.errors.notFound,
        CONFLICT: copy.errors.conflict,
        VALIDATION_ERROR: copy.errors.validation,
        INTERNAL_SERVER_ERROR: copy.errors.server,
      },
      unexpected: copy.errors.unexpected,
      invalidValue: copy.errors.invalidValue,
      invalidData: copy.errors.invalidData,
      network: copy.errors.network,
      httpError: (status) =>
        `${copy.errors.requestFailedPrefix}${status}${copy.errors.requestFailedSuffix}`,
    });

  const canReadUsers = hasPermission("users:read");
  const canReadRoles = hasPermission("roles:read");
  const usersQuery = useQuery({
    queryKey: ["users", search],
    queryFn: () => usersApi.list({ per_page: 100, ...(search.trim() ? { search: search.trim() } : {}) }),
    enabled: sessionReady && canReadUsers,
  });
  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: () => rolesApi.list(),
    enabled: sessionReady && canReadRoles,
  });

  const refreshAccessControl = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["users"] }),
      queryClient.invalidateQueries({ queryKey: ["roles"] }),
      queryClient.invalidateQueries({ queryKey: ["editorial"] }),
    ]);
  };

  const userMutation = useMutation({
    mutationFn: ({ user, payload }: { user: ManagedUser | null; payload: CreateUserPayload | UpdateUserPayload }) =>
      user
        ? usersApi.update(user.id, payload as UpdateUserPayload)
        : usersApi.create(payload as CreateUserPayload),
    onMutate: () => setActionError(""),
    onSuccess: async () => {
      setUserModalOpen(false);
      setEditedUser(null);
      await refreshAccessControl();
    },
    onError: (error) => setActionError(formatActionError(error)),
  });

  const roleMutation = useMutation({
    mutationFn: ({ role, payload }: { role: ManagedRole | null; payload: CreateRolePayload | UpdateRolePayload }) =>
      role
        ? rolesApi.update(role.id, payload as UpdateRolePayload)
        : rolesApi.create(payload as CreateRolePayload),
    onMutate: () => setActionError(""),
    onSuccess: async () => {
      setRoleModalOpen(false);
      setEditedRole(null);
      await refreshAccessControl();
    },
    onError: (error) => setActionError(formatActionError(error)),
  });

  const deactivateUser = useMutation({
    mutationFn: (user: ManagedUser) => usersApi.delete(user.id),
    onMutate: () => setActionError(""),
    onSuccess: refreshAccessControl,
    onError: (error) => setActionError(formatActionError(error)),
  });

  const deleteRole = useMutation({
    mutationFn: (role: ManagedRole) => rolesApi.delete(role.id),
    onMutate: () => setActionError(""),
    onSuccess: refreshAccessControl,
    onError: (error) => setActionError(formatActionError(error)),
  });

  if (!sessionReady) {
    return <div className="py-20 text-center text-sm text-muted-foreground"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />{copy.sessionVerifying}</div>;
  }

  if (!canReadUsers || !canReadRoles) {
    return (
      <section className="mx-auto mt-20 max-w-xl rounded-xl border border-border bg-card p-8 text-center">
        <ShieldAlert className="mx-auto h-10 w-10 text-amber-600" />
        <h1 className="mt-4 text-xl font-semibold">{copy.forbidden.title}</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.forbidden.description}</p>
      </section>
    );
  }

  const users = usersQuery.data?.data.items ?? [];
  const roles = rolesQuery.data?.data.items ?? [];
  const permissions = rolesQuery.data?.data.permissions ?? [];
  const permissionGroups = groupPermissions(permissions, copy);

  const openUserModal = (user: ManagedUser | null) => {
    setActionError("");
    setEditedUser(user);
    setUserModalOpen(true);
  };
  const openRoleModal = (role: ManagedRole | null) => {
    setActionError("");
    setEditedRole(role);
    setRoleModalOpen(true);
  };

  return (
    <div className="mx-auto max-w-[1500px] space-y-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">{copy.header.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.header.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{copy.header.description}</p>
        </div>
        <button
          onClick={() => activeTab === "users" ? openUserModal(null) : openRoleModal(null)}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> {activeTab === "users" ? copy.header.addUserAction : copy.header.addRoleAction}
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-3" aria-label={copy.summaryAriaLabel}>
        <div className="admin-card p-4"><span className="text-xs text-muted-foreground">{copy.summary.accounts}</span><span className="mt-1 block text-2xl font-semibold">{numberFormatter.format(usersQuery.data?.data.total ?? 0)}</span></div>
        <div className="admin-card p-4"><span className="text-xs text-muted-foreground">{copy.summary.activeRoles}</span><span className="mt-1 block text-2xl font-semibold">{numberFormatter.format(roles.length)}</span></div>
        <div className="admin-card p-4"><span className="text-xs text-muted-foreground">{copy.summary.permissions}</span><span className="mt-1 block text-2xl font-semibold">{numberFormatter.format(permissions.length)}</span></div>
      </section>

      <div className="flex border-b border-border" role="tablist" aria-label={copy.tabs.ariaLabel}>
        <button role="tab" aria-selected={activeTab === "users"} onClick={() => setActiveTab("users")} className={cn("flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium", activeTab === "users" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}><Users className="h-4 w-4" /> {copy.tabs.users}</button>
        <button role="tab" aria-selected={activeTab === "matrix"} onClick={() => setActiveTab("matrix")} className={cn("flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium", activeTab === "matrix" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}><KeyRound className="h-4 w-4" /> {copy.tabs.matrix}</button>
      </div>

      <ErrorMessage message={actionError} />

      {activeTab === "users" ? (
        <section className="admin-card overflow-hidden">
          <div className="border-b border-border p-4">
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={copy.users.searchPlaceholder} className="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-[980px] w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-3">{copy.users.table.user}</th><th className="px-4 py-3">{copy.users.table.role}</th><th className="px-4 py-3">{copy.users.table.status}</th><th className="px-4 py-3">{copy.users.table.lastLogin}</th><th className="px-4 py-3 text-right">{copy.users.table.actions}</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {usersQuery.isLoading ? (
                  <tr><td colSpan={5} className="py-14 text-center text-muted-foreground"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />{copy.users.loading}</td></tr>
                ) : usersQuery.isError ? (
                  <tr><td colSpan={5} className="py-14 text-center text-rose-600">{copy.users.loadError}</td></tr>
                ) : users.length === 0 ? (
                  <tr><td colSpan={5} className="py-14 text-center text-muted-foreground">{copy.users.empty}</td></tr>
                ) : users.map((user) => {
                  const protectedAccount = user.id === currentUser?.id || user.roles.includes("super_admin");
                  return (
                    <tr key={user.id} className="hover:bg-muted/20">
                      <td className="px-4 py-4"><p className="font-medium">{user.full_name}</p><p className="mt-1 text-xs text-muted-foreground">{user.email}</p></td>
                      <td className="px-4 py-4"><span className="rounded-md bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{user.primary_role ? (user.primary_role.is_system ? getSystemRoleLabel(user.primary_role.name, roleLabels, user.primary_role.display_name) : user.primary_role.display_name) : (user.roles[0] ? getSystemRoleLabel(user.roles[0], roleLabels, user.roles[0]) : copy.users.noRole)}</span></td>
                      <td className="px-4 py-4"><span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", USER_STATUS_COLORS[user.status])}>{copy.userStatusLabels[user.status]}</span></td>
                      <td className="px-4 py-4 text-xs text-muted-foreground">{user.last_login_at ? formatAdminDateTime(user.last_login_at, locale) : copy.users.neverLoggedIn}</td>
                      <td className="px-4 py-4"><div className="flex justify-end gap-1.5">
                        <button disabled={protectedAccount} title={protectedAccount ? copy.users.editProtectedTitle : copy.users.editTitle} onClick={() => openUserModal(user)} className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"><Pencil className="h-3.5 w-3.5" /> {copy.users.editAction}</button>
                        <button disabled={protectedAccount || user.status === "inactive" || deactivateUser.isPending} title={copy.users.deactivateTitle} onClick={() => { if (window.confirm(`${copy.users.deactivateConfirmPrefix} ${user.full_name}?`)) deactivateUser.mutate(user); }} className="inline-flex h-8 items-center gap-1 rounded-md border border-rose-200 px-2.5 text-xs text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-rose-900/60 dark:text-rose-300 dark:hover:bg-rose-950/30"><Trash2 className="h-3.5 w-3.5" /> {copy.users.deactivateAction}</button>
                      </div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="space-y-4">
          {rolesQuery.isLoading ? (
            <div className="admin-card py-14 text-center text-sm text-muted-foreground"><Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />{copy.roles.loading}</div>
          ) : rolesQuery.isError ? (
            <div className="admin-card py-12 text-center text-sm text-rose-600">
              <p>{copy.roles.loadError}</p>
              <button type="button" onClick={() => rolesQuery.refetch()} className="mt-3 rounded-md border border-border px-3 py-2 text-xs font-medium text-foreground hover:bg-muted">{copy.roles.retryAction}</button>
            </div>
          ) : roles.length === 0 ? (
            <div className="admin-card py-14 text-center text-sm text-muted-foreground">{copy.roles.empty}</div>
          ) : <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {roles.map((role) => (
              <article key={role.id} className="admin-card p-4">
                <div className="flex items-start justify-between gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><ShieldCheck className="h-4 w-4" /></span><span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", role.is_system ? "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" : "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300")}>{role.is_system ? copy.roles.systemBadge : copy.roles.customBadge}</span></div>
                <h2 className="mt-3 font-semibold">{role.is_system ? getSystemRoleLabel(role.name, roleLabels, role.display_name) : role.display_name}</h2>
                <p className="mt-1 min-h-10 text-xs leading-5 text-muted-foreground">{getSystemRoleDescription(role, copy)}</p>
                <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground"><span>{numberFormatter.format(role.user_count)} {copy.roles.usersSuffix}</span><span>{numberFormatter.format(role.permissions.length)} {copy.roles.permissionsSuffix}</span></div>
                {!role.is_system && <div className="mt-3 flex gap-2"><button onClick={() => openRoleModal(role)} className="flex h-8 flex-1 items-center justify-center gap-1 rounded-md border border-border text-xs hover:bg-muted"><Pencil className="h-3.5 w-3.5" /> {copy.roles.editAction}</button><button disabled={role.user_count > 0 || deleteRole.isPending} onClick={() => { if (window.confirm(`${copy.roles.deleteConfirmPrefix} ${role.display_name}?`)) deleteRole.mutate(role); }} title={role.user_count > 0 ? copy.roles.deleteBlockedTitle : copy.roles.deleteTitle} className="flex h-8 items-center justify-center rounded-md border border-rose-200 px-2 text-rose-700 hover:bg-rose-50 disabled:opacity-40 dark:border-rose-900/60 dark:text-rose-300"><Trash2 className="h-3.5 w-3.5" /></button></div>}
              </article>
            ))}
          </div>

          <div className="admin-card overflow-hidden">
            <div className="border-b border-border p-4"><h2 className="font-semibold">{copy.roles.matrixTitle}</h2><p className="mt-1 text-xs text-muted-foreground">{copy.roles.matrixDescription}</p></div>
            <div className="max-h-[680px] overflow-auto">
              <table className="min-w-max w-full text-xs">
                <thead className="sticky top-0 z-10 border-b border-border bg-card shadow-sm"><tr><th className="sticky left-0 z-20 min-w-72 bg-card px-4 py-3 text-left font-semibold">{copy.roles.operation}</th>{roles.map((role) => <th key={role.id} className="min-w-36 px-3 py-3 text-center font-semibold">{role.is_system ? getSystemRoleLabel(role.name, roleLabels, role.display_name) : role.display_name}</th>)}</tr></thead>
                <tbody className="divide-y divide-border">
                  {permissionGroups.map((group) => (
                    <FragmentRows key={group.key} group={group.label} permissions={group.permissions} roles={roles} copy={copy} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          </>}
        </section>
      )}

      <ModalShell open={userModalOpen} onOpenChange={setUserModalOpen} closeAriaLabel={copy.closeDialogAriaLabel} title={editedUser ? copy.userDialog.editTitle : copy.userDialog.createTitle} description={editedUser ? copy.userDialog.editDescription : copy.userDialog.createDescription}>
        <UserForm user={editedUser} roles={roles} pending={userMutation.isPending} error={actionError} copy={copy} roleLabels={roleLabels} onSubmit={(payload) => userMutation.mutate({ user: editedUser, payload })} onCancel={() => setUserModalOpen(false)} />
      </ModalShell>

      <ModalShell open={roleModalOpen} onOpenChange={setRoleModalOpen} closeAriaLabel={copy.closeDialogAriaLabel} title={editedRole ? copy.roleDialog.editTitle : copy.roleDialog.createTitle} description={copy.roleDialog.description}>
        <RoleForm role={editedRole} permissions={permissions} pending={roleMutation.isPending} error={actionError} copy={copy} onSubmit={(payload) => roleMutation.mutate({ role: editedRole, payload })} onCancel={() => setRoleModalOpen(false)} />
      </ModalShell>
    </div>
  );
}

function FragmentRows({
  group,
  permissions,
  roles,
  copy,
}: {
  group: string;
  permissions: PermissionDefinition[];
  roles: ManagedRole[];
  copy: AdminAccessControlDictionary;
}) {
  return (
    <>
      <tr className="bg-muted/45"><th colSpan={roles.length + 1} className="px-4 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{group}</th></tr>
      {permissions.map((permission) => (
        <tr key={permission.key} className="hover:bg-muted/20">
          <th className="sticky left-0 z-[1] bg-card px-4 py-3 text-left font-normal"><span className="block font-medium text-foreground">{getPermissionLabel(permission, copy)}</span><span className="mt-0.5 block text-[10px] text-muted-foreground">{permission.key}</span></th>
          {roles.map((role) => (
            <td key={role.id} className="px-3 py-3 text-center">{role.permissions.includes(permission.key) ? <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" aria-label={copy.roles.allowedAriaLabel}><Check className="h-3.5 w-3.5" /></span> : <span className="text-muted-foreground/35" aria-label={copy.roles.deniedAriaLabel}>—</span>}</td>
          ))}
        </tr>
      ))}
    </>
  );
}
