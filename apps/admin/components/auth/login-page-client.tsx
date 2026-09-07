"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  BookOpenText,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { authApi, getApiErrorMessage } from "@/lib/api";
import type { AdminLoginDictionary } from "@/lib/i18n/types";
import { useAuthStore } from "@/lib/store/auth";

interface LoginForm {
  email: string;
  password: string;
}

function createLoginSchema(validation: AdminLoginDictionary["login"]["validation"]) {
  return z.object({
    email: z.string().email(validation.invalidEmail),
    password: z.string().min(1, validation.requiredPassword),
  });
}

export function LoginPageClient({ dictionary }: { dictionary: AdminLoginDictionary }) {
  const copy = dictionary.login;
  const router = useRouter();
  const { setAccessToken, setAuth } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(createLoginSchema(copy.validation)) });

  const onSubmit = async (data: LoginForm) => {
    setServerError(null);
    try {
      const { data: tokenData } = await authApi.login(data.email, data.password);
      setAccessToken(tokenData.access_token);
      const { data: me } = await authApi.me();
      setAuth(me, tokenData.access_token);
      router.replace("/dashboard");
    } catch (error: unknown) {
      useAuthStore.getState().logout();
      setServerError(
        getApiErrorMessage(error, {
          messagesByCode: {
            UNAUTHORIZED: copy.errors.unauthorized,
            FORBIDDEN: copy.errors.forbidden,
            RATE_LIMITED: copy.errors.rateLimited,
            BAD_REQUEST: copy.errors.validation,
            VALIDATION_ERROR: copy.errors.validation,
            INTERNAL_SERVER_ERROR: copy.errors.server,
          },
          unexpected: copy.errors.unexpected,
          invalidValue: copy.errors.invalidValue,
          invalidData: copy.errors.invalidData,
          network: copy.errors.network,
          httpError: (status) =>
            `${copy.errors.requestFailedPrefix}${status}${copy.errors.requestFailedSuffix}`,
        }),
      );
    }
  };

  return (
    <main className="grid min-h-screen bg-[#f7f7f5] lg:grid-cols-[minmax(25rem,0.9fr)_1.1fr]">
      <section
        className="relative hidden overflow-hidden bg-[#17191c] text-white lg:flex lg:flex-col lg:justify-between lg:p-12"
        aria-label={copy.editorialPanelAriaLabel}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgba(168,132,61,.35), transparent 22rem), repeating-linear-gradient(90deg, transparent 0, transparent 47px, rgba(255,255,255,.035) 48px)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#a8843d]/70 text-[#d2b977]">
            <BookOpenText className="h-5 w-5" />
          </span>
          <div>
            <p className="font-semibold">{dictionary.brand.name}</p>
            <p className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-stone-500">
              {dictionary.brand.product}
            </p>
          </div>
        </div>
        <div className="relative max-w-lg">
          <div className="mb-8 h-px w-20 bg-[#a8843d]" />
          <p className="font-serif text-4xl leading-tight text-stone-100">{copy.quote}</p>
          <p className="mt-5 max-w-md text-sm leading-6 text-stone-400">
            {copy.quoteDescription}
          </p>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-stone-500">
          <ShieldCheck className="h-4 w-4 text-[#a8843d]" />
          {copy.securityStatement}
        </div>
      </section>

      <section className="flex items-center justify-center px-5 py-12 text-[#202225] sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#a8843d] text-[#88672e]">
              <BookOpenText className="h-5 w-5" />
            </span>
            <div>
              <p className="font-semibold">{dictionary.brand.name}</p>
              <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                {dictionary.brand.product}
              </p>
            </div>
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#716b64]">
            {copy.accessKicker}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[#202225]">
            {copy.title}
          </h1>
          <p className="mt-2 text-sm leading-6 text-[#716b64]">{copy.description}</p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-[#202225]">
                {copy.emailLabel}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder={copy.emailPlaceholder}
                {...register("email")}
                className="h-11 w-full rounded-lg border border-[#d5d2cc] bg-white px-3 text-sm text-[#202225] outline-none transition-colors placeholder:text-[#aaa49c] focus:border-[#a8843d]"
              />
              {errors.email && (
                <p className="mt-1.5 text-xs text-[#b3261e]">{errors.email.message}</p>
              )}
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between gap-4">
                <label htmlFor="password" className="text-sm font-medium text-[#202225]">
                  {copy.passwordLabel}
                </label>
                <span className="text-right text-xs font-medium text-[#6b2033]">
                  {copy.passwordRecovery}
                </span>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  {...register("password")}
                  className="h-11 w-full rounded-lg border border-[#d5d2cc] bg-white px-3 pr-11 text-sm text-[#202225] outline-none transition-colors placeholder:text-[#aaa49c] focus:border-[#a8843d]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((show) => !show)}
                  className="absolute right-0 top-0 flex h-11 w-11 items-center justify-center text-[#716b64] hover:text-[#202225]"
                  aria-label={
                    showPassword ? copy.hidePasswordAriaLabel : copy.showPasswordAriaLabel
                  }
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-[#b3261e]">{errors.password.message}</p>
              )}
            </div>
            <p className="text-xs leading-5 text-[#716b64]">{copy.sessionStorageNotice}</p>
            {serverError && (
              <div
                role="alert"
                className="rounded-lg border border-destructive/25 bg-destructive/8 px-3 py-3 text-sm text-destructive"
              >
                {serverError}
              </div>
            )}
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#6b2033] px-4 text-sm font-semibold text-white shadow-sm hover:bg-[#591a2a] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {copy.submitting}
                </>
              ) : (
                <>
                  <LockKeyhole className="h-4 w-4" />
                  {copy.submit}
                </>
              )}
            </button>
          </form>
          <p className="mt-8 border-t border-[#dedbd5] pt-5 text-xs leading-5 text-[#716b64]">
            {copy.auditNotice}
          </p>
        </div>
      </section>
    </main>
  );
}
