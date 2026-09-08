"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  RefreshCw,
  Search,
  Upload,
} from "lucide-react";
import { personsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";
import { SaintAvatar, type SaintAvatarData } from "@/components/persons/saint-avatar";
import { PersonProfileImportDialog } from "@/components/persons/person-profile-import-dialog";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminDomainDictionary,
  AdminEraKey,
  AdminPersonsDictionary,
  AdminPersonTypeKey,
  AdminPublicationStatusKey,
} from "@/lib/i18n/types";
import {
  cn,
  PERSON_STATUS_COLORS,
  PERSON_TYPE_COLORS,
} from "@/lib/utils";

const PER_PAGE = 20;

interface LastEditor {
  full_name: string;
  avatar_url?: string | null;
}

interface AdminPersonListItem {
  id: string;
  canonical_name: string;
  latin_name?: string | null;
  person_type: string;
  status: string;
  era?: string | null;
  last_modified_at?: string | null;
  last_modified_by?: LastEditor | null;
  created_at?: string | null;
  avatar?: SaintAvatarData | null;
}

interface PersonsClientProps {
  copy: AdminPersonsDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}

function EditorIdentity({
  editor,
  systemActor,
}: {
  editor?: LastEditor | null;
  systemActor: string;
}) {
  const name = editor?.full_name ?? systemActor;
  return (
    <div className="flex items-center gap-2">
      <SaintAvatar
        name={name}
        avatar={editor?.avatar_url ? { url: editor.avatar_url } : null}
        className="h-7 w-7 text-[10px]"
      />
      <span className="max-w-40 truncate text-xs text-foreground" title={name}>
        {name}
      </span>
    </div>
  );
}

export function PersonsClient({
  copy,
  domainCopy,
  locale,
}: PersonsClientProps) {
  const router = useRouter();
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canCreate = hasPermission("persons:create");
  const canEdit = hasPermission("persons:update");
  const canImport = hasPermission("import:create");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timeout);
  }, [search]);

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ["persons", page, debouncedSearch, typeFilter, statusFilter],
    queryFn: () =>
      personsApi.adminList({
        page,
        per_page: PER_PAGE,
        ...(debouncedSearch && { search: debouncedSearch }),
        ...(typeFilter && { person_type: typeFilter }),
        ...(statusFilter && { status: statusFilter }),
      }),
  });

  const persons = (data?.data?.items ?? []) as AdminPersonListItem[];
  const total = data?.data?.total ?? 0;
  const pages = data?.data?.pages ?? 1;
  const numberFormatter = new Intl.NumberFormat(locale);

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{copy.header.title}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {copy.header.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canImport && <button onClick={() => setImportOpen(true)} className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-accent"><Upload className="h-4 w-4" /> {copy.header.importAction}</button>}
          {canCreate && (
            <button
              onClick={() => router.push("/dashboard/persons/new")}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              {copy.header.addAction}
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            aria-label={copy.filters.searchAriaLabel}
            placeholder={copy.filters.searchPlaceholder}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        {/* Person type */}
        <select
          aria-label={copy.filters.typeAriaLabel}
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">{copy.filters.allTypes}</option>
          {Object.entries(domainCopy.personTypeLabels).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        {/* Status */}
        <select
          aria-label={copy.filters.statusAriaLabel}
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">{copy.filters.allStatuses}</option>
          {Object.entries(domainCopy.personStatusLabels).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        {/* Refresh */}
        <button
          onClick={() => { void refetch(); }}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
          {copy.filters.refreshAction}
        </button>
      </div>

      {/* Summary */}
      <p className="text-xs text-muted-foreground">
        {copy.resultsPrefix} <strong>{numberFormatter.format(total)}</strong> {copy.resultsSuffix}
      </p>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
        <table aria-label={copy.table.ariaLabel} className="min-w-[1180px] w-full text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.name}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.type}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.status}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.era}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.lastModified}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.modifiedBy}
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {copy.table.createdAt}
              </th>
              <th className="px-4 py-3">
                <span className="sr-only">{copy.table.actions}</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 8 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 w-full animate-pulse rounded bg-muted" />
                    </td>
                  ))}
                </tr>
              ))
            ) : isError ? (
              <tr>
                <td colSpan={8} role="alert" className="px-4 py-12 text-center text-sm text-destructive">
                  {copy.states.loadError}
                </td>
              </tr>
            ) : persons.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  {copy.states.empty}
                </td>
              </tr>
            ) : (
              persons.map((p) => (
                <tr
                  key={p.id}
                  tabIndex={0}
                  aria-label={p.canonical_name}
                  className="cursor-pointer transition-colors hover:bg-muted/40"
                  onClick={() => router.push(`/dashboard/persons/${p.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      router.push(`/dashboard/persons/${p.id}`);
                    }
                  }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <SaintAvatar
                        name={p.canonical_name}
                        avatar={p.avatar}
                        className="h-10 w-10 text-xs"
                      />
                      <div className="min-w-0">
                        <p className="font-medium text-foreground">
                          {p.canonical_name}
                        </p>
                        {Boolean(p.latin_name) && (
                          <p className="text-xs text-muted-foreground italic">
                            {p.latin_name}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium",
                        PERSON_TYPE_COLORS[p.person_type]
                      )}
                    >
                      {domainCopy.personTypeLabels[p.person_type as AdminPersonTypeKey] ?? p.person_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium",
                        PERSON_STATUS_COLORS[p.status]
                      )}
                    >
                      {domainCopy.personStatusLabels[p.status as AdminPublicationStatusKey] ?? p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {p.era ? (domainCopy.eraLabels[p.era as AdminEraKey] ?? p.era) : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatAdminDateTime(p.last_modified_at, locale)}
                  </td>
                  <td className="px-4 py-3">
                    <EditorIdentity editor={p.last_modified_by} systemActor={copy.systemActor} />
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatAdminDateTime(p.created_at, locale)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {canEdit && <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/dashboard/persons/${p.id}/edit`);
                      }}
                      className="rounded-md px-3 py-1 text-xs font-medium text-primary hover:bg-accent"
                    >
                      {copy.editAction}
                    </button>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted-foreground">
            {copy.pagination.pagePrefix} {numberFormatter.format(page)}{" "}
            {copy.pagination.pageSeparator} {numberFormatter.format(pages)}
          </p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-accent transition-colors"
            >
              <ChevronLeft className="h-4 w-4" /> {copy.pagination.previous}
            </button>
            <button
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-accent transition-colors"
            >
              {copy.pagination.next} <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
      <PersonProfileImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        copy={copy.importDialog}
        domainCopy={domainCopy}
      />
    </div>
  );
}
