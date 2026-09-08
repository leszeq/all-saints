"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { useTheme } from "next-themes";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Database,
  Eye,
  EyeOff,
  FileCode2,
  Globe2,
  KeyRound,
  Loader2,
  LockKeyhole,
  Moon,
  RefreshCw,
  Save,
  ServerCog,
  ShieldCheck,
  Sun,
  User,
  type LucideIcon,
} from "lucide-react";
import { useAdminSystemCopy } from "@/components/admin-system-copy-context";
import { API_BASE_URL, authApi, settingsApi } from "@/lib/api";
import { formatAdminApiError } from "@/lib/i18n/api-errors";
import { formatAdminDateTime } from "@/lib/i18n/format";
import type {
  AdminApplicationFeatureKey,
  AdminDomainDictionary,
  AdminEnvironmentKey,
  AdminSettingsDictionary,
  AdminSystemRoleKey,
} from "@/lib/i18n/types";
import { useAuthStore } from "@/lib/store/auth";
import type { ApplicationSettings } from "@/lib/settings";
import { cn } from "@/lib/utils";

function StatusBadge({
  enabled,
  labels,
}: {
  enabled: boolean;
  labels: { on: string; off: string };
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold",
        enabled
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {enabled ? labels.on : labels.off}
    </span>
  );
}

function SectionCard({
  title,
  description,
  icon: Icon,
  children,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <section className="admin-card p-5">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function SettingRow({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <div className="flex flex-col gap-1 border-b border-border py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {detail && <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>}
      </div>
      <div className="text-sm text-foreground/80 sm:text-right">{value}</div>
    </div>
  );
}

function SystemSummary({
  settings,
  copy,
  domainCopy,
  locale,
}: {
  settings: ApplicationSettings;
  copy: AdminSettingsDictionary;
  domainCopy: AdminDomainDictionary;
  locale: string;
}) {
  const docsHref = settings.docs_url ? `${API_BASE_URL}${settings.docs_url}` : "";
  const openApiHref = settings.openapi_url ? `${API_BASE_URL}${settings.openapi_url}` : "";
  const enabledFeatures = useMemo(
    () =>
      Object.entries(settings.features).filter(([, enabled]) => enabled).length,
    [settings.features],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <SectionCard
        title={copy.application.title}
        description={copy.application.description}
        icon={ServerCog}
      >
        <div className="space-y-0">
          <SettingRow label={copy.application.name} value={settings.app_name} />
          <SettingRow label={copy.application.version} value={settings.app_version} />
          <SettingRow
            label={copy.application.environment}
            value={domainCopy.environmentLabels[settings.environment as AdminEnvironmentKey] ?? settings.environment}
          />
          <SettingRow
            label={copy.application.apiDocumentation}
            value={
              settings.security.docs_enabled ? (
                <Link
                  href={docsHref}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-primary hover:underline"
                >
                  {copy.application.swagger}
                </Link>
              ) : (
                copy.common.disabled
              )
            }
          />
          <SettingRow
            label={copy.application.openApi}
            value={
              openApiHref ? (
                <Link
                  href={openApiHref}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-primary hover:underline"
                >
                  {copy.application.schemaJson}
                </Link>
              ) : (
                copy.common.notAvailable
              )
            }
          />
        </div>
      </SectionCard>

      <SectionCard
        title={copy.features.title}
        description={`${new Intl.NumberFormat(locale).format(enabledFeatures)} ${copy.features.descriptionMiddle} ${new Intl.NumberFormat(locale).format(Object.keys(settings.features).length)} ${copy.features.descriptionSuffix}`}
        icon={FileCode2}
      >
        <div className="grid gap-2 sm:grid-cols-2">
          {(Object.entries(settings.features) as Array<[keyof ApplicationSettings["features"], boolean]>).map(
            ([key, enabled]) => (
              <div key={key} className="rounded-xl border border-border bg-muted/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">
                    {domainCopy.applicationFeatureLabels[key as AdminApplicationFeatureKey]}
                  </span>
                  <StatusBadge
                    enabled={enabled}
                    labels={{ on: copy.common.enabled, off: copy.common.disabled }}
                  />
                </div>
                <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
                  {copy.features.environmentNotice}
                </p>
              </div>
            ),
          )}
        </div>
      </SectionCard>

      <SectionCard
        title={copy.ai.title}
        description={copy.ai.description}
        icon={Bot}
      >
        <div className="space-y-0">
          <SettingRow label={copy.ai.provider} value={settings.ai.provider} />
          <SettingRow
            label={copy.ai.openAiApi}
            value={
              <StatusBadge
                enabled={settings.ai.openai_configured}
                labels={{ on: copy.ai.keyConfigured, off: copy.ai.keyMissing }}
              />
            }
          />
          <SettingRow label={copy.ai.embeddingModel} value={settings.ai.embedding_model} />
          <SettingRow label={copy.ai.completionModel} value={settings.ai.completion_model} />
          <SettingRow
            label={copy.ai.ollama}
            value={settings.ai.ollama_base_url ?? copy.ai.ollamaInactive}
          />
          <SettingRow
            label={copy.ai.embeddingDimensions}
            value={new Intl.NumberFormat(locale).format(settings.ai.embedding_dimensions)}
          />
        </div>
      </SectionCard>

      <SectionCard
        title={copy.storageAndSecurity.title}
        description={copy.storageAndSecurity.description}
        icon={ShieldCheck}
      >
        <div className="space-y-0">
          <SettingRow label={copy.storageAndSecurity.storageBackend} value={settings.storage.backend} />
          <SettingRow label={copy.storageAndSecurity.imagesBucket} value={settings.storage.images_bucket} />
          <SettingRow label={copy.storageAndSecurity.documentsBucket} value={settings.storage.documents_bucket} />
          <SettingRow label={copy.storageAndSecurity.exportsBucket} value={settings.storage.exports_bucket} />
          <SettingRow label={copy.storageAndSecurity.publicEndpoint} value={settings.storage.public_endpoint ?? copy.common.notAvailable} />
          <SettingRow
            label={copy.storageAndSecurity.accessToken}
            value={`${new Intl.NumberFormat(locale).format(settings.security.access_token_minutes)} ${copy.storageAndSecurity.minutesSuffix}`}
          />
          <SettingRow
            label={copy.storageAndSecurity.refreshToken}
            value={`${new Intl.NumberFormat(locale).format(settings.security.refresh_token_days)} ${copy.storageAndSecurity.daysSuffix}`}
          />
          <SettingRow
            label={copy.storageAndSecurity.secureCookies}
            value={
              <StatusBadge
                enabled={settings.security.secure_cookies}
                labels={{ on: copy.common.enabled, off: copy.common.disabled }}
              />
            }
          />
          <SettingRow
            label={copy.storageAndSecurity.cors}
            value={settings.security.cors_origins.join(", ") || copy.common.notAvailable}
          />
        </div>
      </SectionCard>
    </div>
  );
}

interface SettingsClientProps {
  copy: AdminSettingsDictionary;
  domainCopy: AdminDomainDictionary;
  roleLabels: Record<AdminSystemRoleKey, string>;
  locale: string;
}

export function SettingsClient({
  copy,
  domainCopy,
  roleLabels,
  locale,
}: SettingsClientProps) {
  const queryClient = useQueryClient();
  const { apiErrors } = useAdminSystemCopy();
  const { resolvedTheme, setTheme } = useTheme();
  const { user, updateUser } = useAuthStore();
  const [fullName, setFullName] = useState<string | null>(null);
  const [preferredLanguage, setPreferredLanguage] = useState<string | null>(null);
  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwords, setPasswords] = useState({
    current: "",
    next: "",
    confirm: "",
  });

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => authApi.me(),
  });

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => settingsApi.get(),
  });

  const currentUser = meQuery.data?.data ?? user;
  const currentLastLoginAt = meQuery.data?.data?.last_login_at ?? null;
  const fullNameValue = fullName ?? currentUser?.full_name ?? "";
  const preferredLanguageValue =
    preferredLanguage ?? currentUser?.preferred_language ?? "pl";
  const settings = settingsQuery.data?.data;
  const loading = meQuery.isLoading || settingsQuery.isLoading;
  const localizedRoles =
    currentUser?.roles
      .map((role) => roleLabels[role as AdminSystemRoleKey] ?? role)
      .join(", ") || copy.common.notAvailable;

  const profileMutation = useMutation({
    mutationFn: () =>
      authApi.updateProfile({
        full_name: fullNameValue.trim(),
        preferred_language: preferredLanguageValue,
      }),
    onMutate: () => setProfileMessage(""),
    onSuccess: async (response) => {
      setFullName(response.data.full_name);
      setPreferredLanguage(response.data.preferred_language);
      updateUser(response.data);
      setProfileMessage(copy.profile.profileSaved);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });

  const passwordMutation = useMutation({
    mutationFn: () => authApi.changePassword(passwords.current, passwords.next),
    onMutate: () => {
      setPasswordMessage("");
      setPasswordError("");
    },
    onSuccess: () => {
      setPasswords({ current: "", next: "", confirm: "" });
      setPasswordMessage(copy.password.changed);
    },
    onError: (error) => setPasswordError(formatAdminApiError(error, apiErrors)),
  });

  const profileError = profileMutation.error
    ? formatAdminApiError(profileMutation.error, apiErrors)
    : "";

  const submitPassword = () => {
    setPasswordError("");
    if (passwords.next.length < 8) {
      setPasswordError(copy.password.tooShort);
      return;
    }
    if (passwords.next !== passwords.confirm) {
      setPasswordError(copy.password.mismatch);
      return;
    }
    passwordMutation.mutate();
  };

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> {copy.loading}
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">{copy.loadError.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {copy.loadError.description}
        </p>
        <button
          onClick={() => settingsQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          {copy.loadError.refreshAction}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">{copy.header.kicker}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{copy.header.title}</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            {copy.header.description}
          </p>
        </div>
        <button
          onClick={() => {
            meQuery.refetch();
            settingsQuery.refetch();
          }}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent"
        >
          <RefreshCw
            className={cn(
              "h-4 w-4",
              (meQuery.isFetching || settingsQuery.isFetching) && "animate-spin",
            )}
          />
          {copy.header.refreshAction}
        </button>
      </header>

      <section className="grid gap-5 xl:grid-cols-[.85fr_1.15fr]">
        <div className="space-y-5">
          <SectionCard
            title={copy.profile.title}
            description={copy.profile.description}
            icon={User}
          >
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  {copy.profile.fullName}
                </label>
                <input
                  value={fullNameValue}
                  onChange={(event) => setFullName(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                  placeholder={copy.profile.fullNamePlaceholder}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  {copy.profile.preferredLanguage}
                </label>
                <select
                  value={preferredLanguageValue}
                  onChange={(event) => setPreferredLanguage(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="pl">{copy.profile.languages.pl}</option>
                  <option value="en">{copy.profile.languages.en}</option>
                  <option value="la">{copy.profile.languages.la}</option>
                </select>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs leading-5 text-muted-foreground">
                <p>
                  {copy.profile.email} <span className="font-medium text-foreground">{currentUser?.email ?? copy.common.notAvailable}</span>
                </p>
                <p>
                  {copy.profile.roles} <span className="font-medium text-foreground">{localizedRoles}</span>
                </p>
                <p>
                  {copy.profile.lastLogin}{" "}
                  <span className="font-medium text-foreground">
                    {formatAdminDateTime(currentLastLoginAt, locale)}
                  </span>
                </p>
              </div>
              {profileMessage && (
                <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
                  <CheckCircle2 className="h-4 w-4" /> {profileMessage}
                </p>
              )}
              {profileError && (
                <p className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                  <AlertTriangle className="h-4 w-4" /> {profileError}
                </p>
              )}
              <button
                disabled={profileMutation.isPending || !fullNameValue.trim()}
                onClick={() => profileMutation.mutate()}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {profileMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                {copy.profile.saveAction}
              </button>
            </div>
          </SectionCard>

          <SectionCard
            title={copy.appearance.title}
            description={copy.appearance.description}
            icon={Globe2}
          >
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                onClick={() => setTheme("light")}
                className={cn(
                  "rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40",
                  resolvedTheme === "light" && "border-primary bg-primary/[0.04] ring-1 ring-primary/20",
                )}
              >
                <Sun className="h-4 w-4 text-primary" />
                <span className="mt-3 block text-sm font-semibold">{copy.appearance.light}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{copy.appearance.lightDescription}</span>
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={cn(
                  "rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40",
                  resolvedTheme === "dark" && "border-primary bg-primary/[0.04] ring-1 ring-primary/20",
                )}
              >
                <Moon className="h-4 w-4 text-primary" />
                <span className="mt-3 block text-sm font-semibold">{copy.appearance.dark}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{copy.appearance.darkDescription}</span>
              </button>
            </div>
          </SectionCard>

          <SectionCard
            title={copy.password.title}
            description={copy.password.description}
            icon={LockKeyhole}
          >
            <div className="space-y-4">
              {[
                { key: "current", label: copy.password.current, autoComplete: "current-password" },
                { key: "next", label: copy.password.next, autoComplete: "new-password" },
                { key: "confirm", label: copy.password.confirm, autoComplete: "new-password" },
              ].map((field) => (
                <div key={field.key}>
                  <label className="mb-1 block text-sm font-medium text-foreground">
                    {field.label}
                  </label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type={showPassword ? "text" : "password"}
                      autoComplete={field.autoComplete}
                      value={passwords[field.key as keyof typeof passwords]}
                      onChange={(event) =>
                        setPasswords((current) => ({
                          ...current,
                          [field.key]: event.target.value,
                        }))
                      }
                      className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-10 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((visible) => !visible)}
                      className="absolute right-0 top-0 flex h-10 w-10 items-center justify-center text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? copy.password.hideAriaLabel : copy.password.showAriaLabel}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              ))}
              {passwordMessage && (
                <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
                  <CheckCircle2 className="h-4 w-4" /> {passwordMessage}
                </p>
              )}
              {passwordError && (
                <p className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                  <AlertTriangle className="h-4 w-4" /> {passwordError}
                </p>
              )}
              <button
                disabled={
                  passwordMutation.isPending ||
                  !passwords.current ||
                  !passwords.next ||
                  !passwords.confirm
                }
                onClick={submitPassword}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-border px-4 text-sm font-semibold hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
              >
                {passwordMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )}
                {copy.password.changeAction}
              </button>
            </div>
          </SectionCard>
        </div>

        <div className="space-y-5">
          <SystemSummary
            settings={settings}
            copy={copy}
            domainCopy={domainCopy}
            locale={locale}
          />
          <SectionCard
            title={copy.environment.title}
            description={copy.environment.description}
            icon={Database}
          >
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              <p className="font-semibold">{copy.environment.explanationTitle}</p>
              <p className="mt-1">
                {copy.environment.explanation}
              </p>
            </div>
          </SectionCard>
        </div>
      </section>
    </div>
  );
}
