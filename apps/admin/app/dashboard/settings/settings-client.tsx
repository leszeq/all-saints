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
import { API_BASE_URL, authApi, getApiErrorMessage, settingsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store/auth";
import {
  ENVIRONMENT_LABELS,
  FEATURE_LABELS,
  type ApplicationSettings,
} from "@/lib/settings";
import { cn, formatDateTime } from "@/lib/utils";

function StatusBadge({
  enabled,
  label,
}: {
  enabled: boolean;
  label?: { on: string; off: string };
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
      {enabled ? label?.on ?? "Włączone" : label?.off ?? "Wyłączone"}
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

function SystemSummary({ settings }: { settings: ApplicationSettings }) {
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
        title="Aplikacja"
        description="Podstawowe informacje o środowisku i dokumentacji API."
        icon={ServerCog}
      >
        <div className="space-y-0">
          <SettingRow label="Nazwa" value={settings.app_name} />
          <SettingRow label="Wersja" value={settings.app_version} />
          <SettingRow
            label="Środowisko"
            value={ENVIRONMENT_LABELS[settings.environment] ?? settings.environment}
          />
          <SettingRow
            label="Dokumentacja API"
            value={
              settings.security.docs_enabled ? (
                <Link
                  href={docsHref}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-primary hover:underline"
                >
                  Swagger
                </Link>
              ) : (
                "Wyłączona"
              )
            }
          />
          <SettingRow
            label="OpenAPI"
            value={
              openApiHref ? (
                <Link
                  href={openApiHref}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-primary hover:underline"
                >
                  Schema JSON
                </Link>
              ) : (
                "—"
              )
            }
          />
        </div>
      </SectionCard>

      <SectionCard
        title="Funkcje"
        description={`${enabledFeatures} z ${Object.keys(settings.features).length} modułów jest aktualnie włączonych.`}
        icon={FileCode2}
      >
        <div className="grid gap-2 sm:grid-cols-2">
          {(Object.entries(settings.features) as Array<[keyof ApplicationSettings["features"], boolean]>).map(
            ([key, enabled]) => (
              <div key={key} className="rounded-xl border border-border bg-muted/20 p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">{FEATURE_LABELS[key]}</span>
                  <StatusBadge enabled={enabled} />
                </div>
                <p className="mt-2 text-[11px] leading-4 text-muted-foreground">
                  Zmieniane przez konfigurację środowiskową backendu.
                </p>
              </div>
            ),
          )}
        </div>
      </SectionCard>

      <SectionCard
        title="AI"
        description="Konfiguracja providera, modeli i wymiaru embeddingów."
        icon={Bot}
      >
        <div className="space-y-0">
          <SettingRow label="Provider" value={settings.ai.provider} />
          <SettingRow
            label="OpenAI API"
            value={
              <StatusBadge
                enabled={settings.ai.openai_configured}
                label={{ on: "Klucz ustawiony", off: "Brak klucza" }}
              />
            }
          />
          <SettingRow label="Model embeddingów" value={settings.ai.embedding_model} />
          <SettingRow label="Model streszczeń" value={settings.ai.completion_model} />
          <SettingRow
            label="Ollama"
            value={settings.ai.ollama_base_url ?? "Nieaktywna"}
          />
          <SettingRow
            label="Wymiar embeddingów"
            value={settings.ai.embedding_dimensions.toLocaleString("pl-PL")}
          />
        </div>
      </SectionCard>

      <SectionCard
        title="Storage i bezpieczeństwo"
        description="Podgląd sposobu przechowywania mediów oraz parametrów sesji."
        icon={ShieldCheck}
      >
        <div className="space-y-0">
          <SettingRow label="Storage backend" value={settings.storage.backend} />
          <SettingRow label="Bucket obrazów" value={settings.storage.images_bucket} />
          <SettingRow label="Bucket dokumentów" value={settings.storage.documents_bucket} />
          <SettingRow label="Bucket eksportów" value={settings.storage.exports_bucket} />
          <SettingRow label="Endpoint publiczny" value={settings.storage.public_endpoint ?? "—"} />
          <SettingRow
            label="Access token"
            value={`${settings.security.access_token_minutes} min`}
          />
          <SettingRow
            label="Refresh token"
            value={`${settings.security.refresh_token_days} dni`}
          />
          <SettingRow
            label="Secure cookies"
            value={<StatusBadge enabled={settings.security.secure_cookies} />}
          />
          <SettingRow
            label="CORS"
            value={settings.security.cors_origins.join(", ") || "—"}
          />
        </div>
      </SectionCard>
    </div>
  );
}

export function SettingsClient() {
  const queryClient = useQueryClient();
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
      setProfileMessage("Profil został zapisany.");
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
      setPasswordMessage("Hasło zostało zmienione.");
    },
    onError: (error) => setPasswordError(getApiErrorMessage(error)),
  });

  const profileError = profileMutation.error ? getApiErrorMessage(profileMutation.error) : "";

  const submitPassword = () => {
    setPasswordError("");
    if (passwords.next.length < 8) {
      setPasswordError("Nowe hasło musi mieć minimum 8 znaków.");
      return;
    }
    if (passwords.next !== passwords.confirm) {
      setPasswordError("Powtórzone hasło nie jest takie samo.");
      return;
    }
    passwordMutation.mutate();
  };

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Ładowanie ustawień…
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="admin-card mx-auto max-w-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-amber-500" />
        <h1 className="mt-3 text-lg font-semibold">Nie udało się pobrać ustawień</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sprawdź połączenie z API i spróbuj ponownie.
        </p>
        <button
          onClick={() => settingsQuery.refetch()}
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          Odśwież dane
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="admin-label">Administracja</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Ustawienia</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Zarządzaj swoim kontem redakcyjnym i sprawdzaj bezpieczny podgląd konfiguracji systemu.
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
          Odśwież
        </button>
      </header>

      <section className="grid gap-5 xl:grid-cols-[.85fr_1.15fr]">
        <div className="space-y-5">
          <SectionCard
            title="Konto redakcyjne"
            description="Dane widoczne w panelu, historii zmian i kolejce redakcyjnej."
            icon={User}
          >
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Imię i nazwisko
                </label>
                <input
                  value={fullNameValue}
                  onChange={(event) => setFullName(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                  placeholder="Jan Redaktor"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground">
                  Preferowany język
                </label>
                <select
                  value={preferredLanguageValue}
                  onChange={(event) => setPreferredLanguage(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="pl">Polski</option>
                  <option value="en">English</option>
                  <option value="la">Łacina</option>
                </select>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs leading-5 text-muted-foreground">
                <p>
                  E-mail: <span className="font-medium text-foreground">{currentUser?.email ?? "—"}</span>
                </p>
                <p>
                  Role: <span className="font-medium text-foreground">{currentUser?.roles.join(", ") || "—"}</span>
                </p>
                <p>
                  Ostatnie logowanie:{" "}
                  <span className="font-medium text-foreground">
                    {formatDateTime(currentLastLoginAt)}
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
                Zapisz profil
              </button>
            </div>
          </SectionCard>

          <SectionCard
            title="Wygląd panelu"
            description="Preferencje interfejsu zapisywane lokalnie w przeglądarce."
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
                <span className="mt-3 block text-sm font-semibold">Jasny</span>
                <span className="mt-1 block text-xs text-muted-foreground">Klasyczny tryb redakcyjny.</span>
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={cn(
                  "rounded-xl border border-border p-4 text-left transition-colors hover:border-primary/40",
                  resolvedTheme === "dark" && "border-primary bg-primary/[0.04] ring-1 ring-primary/20",
                )}
              >
                <Moon className="h-4 w-4 text-primary" />
                <span className="mt-3 block text-sm font-semibold">Ciemny</span>
                <span className="mt-1 block text-xs text-muted-foreground">Wygodny przy dłuższej pracy wieczorem.</span>
              </button>
            </div>
          </SectionCard>

          <SectionCard
            title="Zmiana hasła"
            description="Hasło powinno być unikalne i zgodne z polityką bezpieczeństwa backendu."
            icon={LockKeyhole}
          >
            <div className="space-y-4">
              {[
                { key: "current", label: "Obecne hasło", autoComplete: "current-password" },
                { key: "next", label: "Nowe hasło", autoComplete: "new-password" },
                { key: "confirm", label: "Powtórz nowe hasło", autoComplete: "new-password" },
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
                      aria-label={showPassword ? "Ukryj hasła" : "Pokaż hasła"}
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
                Zmień hasło
              </button>
            </div>
          </SectionCard>
        </div>

        <div className="space-y-5">
          <SystemSummary settings={settings} />
          <SectionCard
            title="Konfiguracja przez środowisko"
            description="Te wartości są odczytywane z backendu i powinny być zmieniane w `.env` albo konfiguracji deploymentu."
            icon={Database}
          >
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              <p className="font-semibold">Dlaczego read-only?</p>
              <p className="mt-1">
                Ustawienia takie jak provider AI, storage, CORS i długość sesji wpływają
                na bezpieczeństwo całego systemu. Panel pokazuje ich stan, ale ich zmiana
                powinna przejść przez świadomy deploy.
              </p>
            </div>
          </SectionCard>
        </div>
      </section>
    </div>
  );
}
