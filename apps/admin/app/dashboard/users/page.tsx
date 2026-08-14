"use client";

import { useQuery } from "@tanstack/react-query";
import { UserCheck, Users } from "lucide-react";
import { usersApi } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function UsersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
  });

  const users = data?.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Użytkownicy i Uprawnienia</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Zarządzaj kontami użytkowników i przypisanymi rolami systemowymi
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/40 text-left text-xs font-semibold text-muted-foreground uppercase">
            <tr>
              <th className="px-4 py-3">Użytkownik</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Ostatnie logowanie</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Ładowanie...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  Brak użytkowników
                </td>
              </tr>
            ) : (
              users.map((u: Record<string, unknown>) => (
                <tr key={u.id as string} className="hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium text-foreground">
                    {u.full_name as string}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {u.email as string}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(u.roles as string[])?.map((r) => (
                        <span
                          key={r}
                          className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
                      {u.status as string}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {formatDateTime(u.last_login_at as string)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
