"use client";

import { Bell, LogOut, Moon, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { authApi } from "@/lib/api";

interface TopbarProps {
  title?: string;
}

export function Topbar({ title }: TopbarProps) {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      logout();
      router.push("/login");
    }
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div>
        {title && (
          <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          title="Zmień motyw"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        {/* Notifications */}
        <button className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground">
          <Bell className="h-4 w-4" />
        </button>

        {/* User info */}
        <div className="ml-2 flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden flex-col sm:flex">
            <span className="text-[13px] font-medium text-foreground leading-none">
              {user?.full_name || "Admin"}
            </span>
            <span className="mt-0.5 text-[11px] text-muted-foreground leading-none">
              {user?.roles?.[0] || ""}
            </span>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="ml-1 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          title="Wyloguj"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
