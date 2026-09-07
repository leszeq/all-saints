import type { Metadata } from "next";

import {
  EditorialQueueClient,
  type EditorialQueueInitialFilters,
} from "./review-client";
import type { EditorialPriority } from "@/lib/editorial";
import { DEFAULT_ADMIN_UI_LOCALE } from "@/lib/i18n/config";
import { getAdminDictionary } from "@/lib/i18n/dictionaries";

type SearchParams = Promise<{
  status?: string | string[];
  priority?: string | string[];
  attention?: string | string[];
}>;

const queueStatuses = new Set(["draft", "review"]);
const queuePriorities = new Set(["urgent", "high", "normal"]);

function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export async function generateMetadata(): Promise<Metadata> {
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);
  return {
    title: dictionary.review.metadataTitle,
    description: dictionary.review.metadataDescription,
  };
}

export default async function EditorialQueuePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const statusParam = firstParam(params.status);
  const priorityParam = firstParam(params.priority);
  const attentionParam = firstParam(params.attention);

  const initialFilters: EditorialQueueInitialFilters = {
    status: queueStatuses.has(statusParam ?? "")
      ? (statusParam as EditorialQueueInitialFilters["status"])
      : "",
    priority: queuePriorities.has(priorityParam ?? "")
      ? (priorityParam as EditorialPriority)
      : "",
    attention: attentionParam === "1" || attentionParam === "true",
  };
  const filterKey = `${initialFilters.status}:${initialFilters.priority}:${initialFilters.attention}`;
  const dictionary = await getAdminDictionary(DEFAULT_ADMIN_UI_LOCALE);

  return (
    <EditorialQueueClient
      key={filterKey}
      initialFilters={initialFilters}
      copy={dictionary.review}
      domainCopy={dictionary.domain}
      locale={DEFAULT_ADMIN_UI_LOCALE}
    />
  );
}
