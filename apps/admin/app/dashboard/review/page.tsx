import {
  EditorialQueueClient,
  type EditorialQueueInitialFilters,
} from "./review-client";
import type { EditorialPriority } from "@/lib/editorial";

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

  return <EditorialQueueClient key={filterKey} initialFilters={initialFilters} />;
}
