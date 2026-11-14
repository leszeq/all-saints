import { expect, test, type APIRequestContext } from "@playwright/test";

const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

type PublicIndexItem = {
  id: string;
  slug: string;
};

function sitemapLocations(xml: string): string[] {
  return Array.from(xml.matchAll(/<loc>([^<]+)<\/loc>/g), ([, value]) =>
    value
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">"),
  );
}

async function getFirstPublicPerson(request: APIRequestContext): Promise<PublicIndexItem> {
  const response = await request.get(`${apiUrl}/public-index/persons?limit=1`);
  expect(response.status(), "public index API powinien być dostępny").toBe(200);
  const payload = (await response.json()) as { items?: PublicIndexItem[] };
  const person = payload.items?.[0];
  expect(person, "fixture musi zawierać opublikowany profil").toBeTruthy();
  if (!person) throw new Error("Brak opublikowanego profilu w publicznym indeksie");
  return person;
}

test("crawler endpoints expose one canonical public profile URL", async ({ page, request }) => {
  const [robotsResponse, sitemapResponse, person] = await Promise.all([
    request.get(`${webUrl}/robots.txt`),
    request.get(`${webUrl}/sitemap.xml`),
    getFirstPublicPerson(request),
  ]);

  expect(robotsResponse.status()).toBe(200);
  expect(await robotsResponse.text()).toMatch(/Sitemap:\s*\S+\/sitemap\.xml/i);

  expect(sitemapResponse.status()).toBe(200);
  const sitemap = sitemapLocations(await sitemapResponse.text());
  const profilePath = `/swieci/${encodeURIComponent(person.slug)}`;
  const profileLocation = sitemap.find((location) => new URL(location).pathname === profilePath);
  expect(profileLocation, "sitemap powinien zawierać profil z publicznego indeksu").toBeTruthy();

  const canonicalResponse = await request.get(`${webUrl}${profilePath}`, {
    maxRedirects: 0,
  });
  expect(canonicalResponse.status()).toBe(200);
  const canonicalHtml = await canonicalResponse.text();
  const canonicalHref = canonicalHtml.match(/<link rel="canonical" href="([^"]+)"/i)?.[1];
  expect(canonicalHref, "profil powinien mieć link canonical").toBeTruthy();
  expect(new URL(canonicalHref!, webUrl).pathname).toBe(profilePath);

  const uuidResponse = await page.goto(`${webUrl}/swieci/${person.id}`);
  expect(uuidResponse?.status()).toBe(200);
  await expect(page).toHaveURL(new URL(profilePath, webUrl).toString());
});
