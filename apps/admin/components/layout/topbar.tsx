"use client";

import { Bell, Command, LogOut, Moon, Search, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { authApi } from "@/lib/api";
import type { AdminSystemRoleKey, AdminTopbarDictionary } from "@/lib/i18n/types";

interface TopbarProps { title?: string; }

export function Topbar({ title, dictionary }: TopbarProps & { dictionary: AdminTopbarDictionary }) {
  const { resolvedTheme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const role = user?.roles?.[0];
  const roleLabel = role
    ? dictionary.roleLabels[role as AdminSystemRoleKey] ?? role
    : dictionary.noRoleFallback;

  const handleLogout = async () => {
    try { await authApi.logout(); } finally { logout(); router.push("/login"); }
  };

  return (
    <header className="flex h-16 shrink-0 items-center gap-5 border-b border-border bg-card px-6">
      {title && <h1 className="text-base font-semibold text-foreground">{title}</h1>}
      <button type="button" className="flex h-9 w-full max-w-md items-center gap-2 rounded-lg border border-input bg-background px-3 text-sm text-muted-foreground transition-colors hover:border-ring/60" aria-label={dictionary.globalSearchAriaLabel}>
        <Search className="h-4 w-4" /><span className="flex-1 text-left">{dictionary.globalSearchPlaceholder}</span><span className="flex items-center gap-1 rounded border border-border bg-card px-1.5 py-0.5 text-[10px]"><Command className="h-2.5 w-2.5" />K</span>
      </button>
      <div className="ml-auto flex items-center gap-1">
        <button type="button" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={dictionary.changeThemeAriaLabel}><Moon className="h-4 w-4 dark:hidden" /><Sun className="hidden h-4 w-4 dark:block" /></button>
        <button type="button" className="relative flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={dictionary.notificationsAriaLabel}><Bell className="h-4 w-4" /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary ring-2 ring-card" /></button>
        <div className="mx-2 h-7 w-px bg-border" />
        <div className="flex items-center gap-2.5"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary"><User className="h-4 w-4" /></span><span className="hidden sm:block"><span className="block text-[12px] font-semibold leading-none">{user?.full_name || dictionary.userFallback}</span><span className="mt-1 block text-[10px] text-muted-foreground">{roleLabel}</span></span></div>
        <button type="button" onClick={handleLogout} className="ml-1 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive" aria-label={dictionary.logoutAriaLabel}><LogOut className="h-4 w-4" /></button>
      </div>
    </header>
  );
}
