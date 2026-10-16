import type { MetadataRoute } from "next";
import { fetchOrders, fetchPublicPersonIndex } from "@/lib/api";
import { absoluteSiteUrl } from "@/lib/site-url";

type SitemapPerson = {
  slug?: string;
  updated_at?: string;
};

type SitemapOrder = {
  slug?: string;
  updated_at?: string;
};

type PersonPage = {
  items?: SitemapPerson[];
  next_cursor?: string | null;
};

function lastModified(value?: string): Date | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

async function fetchAllPersons(): Promise<SitemapPerson[]> {
  const people: SitemapPerson[] = [];
  let cursor: string | undefined;

  do {
    const result = (await fetchPublicPersonIndex({
      cursor,
      limit: 100,
    })) as PersonPage;
    people.push(...(result.items ?? []));
    cursor = result.next_cursor ?? undefined;
  } while (cursor);

  return people;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticEntries: MetadataRoute.Sitemap = [
    { url: absoluteSiteUrl("/"), changeFrequency: "weekly", priority: 1 },
    { url: absoluteSiteUrl("/swieci"), changeFrequency: "daily", priority: 0.9 },
    { url: absoluteSiteUrl("/zakony"), changeFrequency: "weekly", priority: 0.7 },
    { url: absoluteSiteUrl("/kalendarz"), changeFrequency: "daily", priority: 0.7 },
  ];

  try {
    const [people, orders] = await Promise.all([
      fetchAllPersons(),
      fetchOrders() as Promise<SitemapOrder[]>,
    ]);

    return [
      ...staticEntries,
      ...people
        .filter((person): person is SitemapPerson & { slug: string } => Boolean(person.slug))
        .map((person) => ({
          url: absoluteSiteUrl(`/swieci/${encodeURIComponent(person.slug)}`),
          lastModified: lastModified(person.updated_at),
          changeFrequency: "monthly" as const,
          priority: 0.8,
        })),
      ...orders
        .filter((order): order is SitemapOrder & { slug: string } => Boolean(order.slug))
        .map((order) => ({
          url: absoluteSiteUrl(`/zakony/${encodeURIComponent(order.slug)}`),
          lastModified: lastModified(order.updated_at),
          changeFrequency: "monthly" as const,
          priority: 0.6,
        })),
    ];
  } catch {
    // Keep the crawler entry point available during an API/database outage.
    return staticEntries;
  }
}
