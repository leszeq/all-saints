"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  recordProductEvent,
  type ProductFilterName,
  type ProductQueryClass,
  type ProductSourceKind,
} from "@/lib/analytics";

const PROFILE_PATH = /^\/swieci\/[^/]+\/?$/;
const ORDER_PATH = /^\/zakony\/[^/]+\/?$/;
const recordedResultPages = new Set<string>();

const FILTER_NAMES: Record<string, ProductFilterName> = {
  type: "person_type",
  gender: "gender",
  period: "period",
  era: "period",
  patronage: "patronage",
  order_id: "order",
  occupation_id: "occupation",
  birth_country_id: "birth_country",
  death_country_id: "death_country",
  nationality_id: "nationality",
};

function getFilterName(form: HTMLFormElement): ProductFilterName | undefined {
  const activeElement = document.activeElement;
  if (!(activeElement instanceof HTMLInputElement || activeElement instanceof HTMLSelectElement)) {
    return undefined;
  }
  if (!form.contains(activeElement)) return undefined;
  return FILTER_NAMES[activeElement.name];
}

function getQueryClass(form: HTMLFormElement): ProductQueryClass {
  const search = form.querySelector<HTMLInputElement>('input[name="search"]');
  return search?.value.trim() ? "name" : "filter";
}

function hasActiveFilter(form: HTMLFormElement): boolean {
  return Boolean(
    form.querySelector('input[type="checkbox"]:checked') ||
      Array.from(form.querySelectorAll("select")).some((select) => select.value),
  );
}

function handleFormSubmit(event: SubmitEvent): void {
  if (!(event.target instanceof HTMLFormElement)) return;
  const form = event.target;
  if (!form.querySelector('input[name="search"]')) return;

  const hasSearch = Boolean(form.querySelector<HTMLInputElement>('input[name="search"]')?.value.trim());
  const eventName = hasSearch ? "search_submitted" : "filter_applied";
  recordProductEvent(eventName, {
    query_class: getQueryClass(form),
    ...(hasActiveFilter(form) && { properties: { filter_name: getFilterName(form) } }),
  });
}

function sourceKind(link: HTMLAnchorElement): ProductSourceKind {
  const value = link.dataset.analyticsSourceKind;
  return value === "bibliography" || value === "historical" || value === "image" ? value : "web";
}

function handleLinkClick(event: MouseEvent): void {
  if (!(event.target instanceof Element)) return;
  const link = event.target.closest<HTMLAnchorElement>("a[href]");
  if (!link) return;

  const url = new URL(link.href, window.location.href);
  if (url.origin === window.location.origin && PROFILE_PATH.test(url.pathname)) {
    recordProductEvent("profile_opened");
    return;
  }

  if (url.origin === window.location.origin && ORDER_PATH.test(url.pathname)) {
    recordProductEvent("relation_opened", { properties: { relation_kind: "order" } });
    return;
  }

  if (link.closest("#bibliografia") && url.origin !== window.location.origin) {
    recordProductEvent("source_opened", { properties: { source_kind: sourceKind(link) } });
  }
}

export function ProductAnalytics() {
  const pathname = usePathname();

  useEffect(() => {
    document.addEventListener("submit", handleFormSubmit, true);
    document.addEventListener("click", handleLinkClick, true);

    return () => {
      document.removeEventListener("submit", handleFormSubmit, true);
      document.removeEventListener("click", handleLinkClick, true);
    };
  }, []);

  useEffect(() => {
    if (pathname !== "/swieci") return;

    const resultPageKey = `${pathname}${window.location.search}`;
    if (recordedResultPages.has(resultPageKey)) return;
    recordedResultPages.add(resultPageKey);

    const resultCount = Number(
      document.querySelector<HTMLElement>("[data-analytics-result-count]")?.dataset.analyticsResultCount,
    );
    const queryClass: ProductQueryClass = new URLSearchParams(window.location.search).has("search")
      ? "name"
      : "filter";
    recordProductEvent("search_results", {
      query_class: queryClass,
      ...(Number.isFinite(resultCount) && {
        properties: { result_count: Math.max(0, Math.min(10_000, resultCount)) },
      }),
    });
  }, [pathname]);

  return null;
}
