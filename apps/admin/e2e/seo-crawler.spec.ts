import { expect, test, type APIRequestContext } from "@playwright/test";

const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";
const password = process.env.E2E_PASSWORD ?? "DemoE2E123!";

const accounts = {
  admin: process.env.E2E_ADMIN_EMAIL ?? "admin.test@encyklopedia.pl",
  editor: process.env.E2E_EDITOR_EMAIL ?? "redaktor.test@encyklopedia.pl",
  reviewer: process.env.E2E_REVIEWER_EMAIL ?? "recenzent.test@encyklopedia.pl",
};

type PublicIndexItem = {
  id: string;
  slug: string;
};

type LoginResponse = {
  access_token: string;
};

type CreatedPerson = {
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

async function loginAs(request: APIRequestContext, email: string): Promise<string> {
  const response = await request.post(`${apiUrl}/auth/login`, {
    data: { email, password },
  });
  expect(response.ok(), `Logowanie konta testowego ${email}`).toBeTruthy();
  const payload = (await response.json()) as LoginResponse;
  return payload.access_token;
}

function authorization(token: string) {
  return { Authorization: `Bearer ${token}` };
}

async function sitemapHasProfile(request: APIRequestContext, slug: string): Promise<boolean> {
  const response = await request.get(`${webUrl}/sitemap.xml`);
  expect(response.status(), "sitemap powinien być dostępny").toBe(200);
  const locations = sitemapLocations(await response.text());
  const profilePath = `/swieci/${encodeURIComponent(slug)}`;
  return locations.some((location) => new URL(location).pathname === profilePath);
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

test("publikacja i usunięcie profilu odświeżają sitemapę", async ({ request }) => {
  const editorToken = await loginAs(request, accounts.editor);
  const reviewerToken = await loginAs(request, accounts.reviewer);
  const uniqueSuffix = `${Date.now()}-${test.info().workerIndex}`;
  let person: CreatedPerson | null = null;

  try {
    const createResponse = await request.post(`${apiUrl}/persons`, {
      headers: authorization(editorToken),
      data: {
        canonical_name: `Św. Sitemap E2E ${uniqueSuffix}`,
        person_type: "saint",
        status: "draft",
        gender: "unknown",
        summary_pl: "Profil techniczny do sprawdzenia odświeżania sitemap.",
        biography_pl: "Profil techniczny do sprawdzenia cyklu publikacji i usunięcia.",
      },
    });
    expect(createResponse.status()).toBe(201);
    person = (await createResponse.json()) as CreatedPerson;

    await expect.poll(() => sitemapHasProfile(request, person!.slug)).toBe(false);

    const reviewResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(editorToken),
        data: { target_status: "review", expected_version: 1 },
      },
    );
    expect(reviewResponse.status()).toBe(200);

    const sourceResponse = await request.post(`${apiUrl}/sources/person-links/${person.id}/web`, {
      headers: authorization(editorToken),
      data: {
        title: "Źródło testowego profilu sitemap",
        url: `https://example.test/sitemap/${uniqueSuffix}`,
        is_primary: true,
      },
    });
    expect(sourceResponse.status()).toBe(201);

    const publishResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(reviewerToken),
        data: { target_status: "published", expected_version: 3 },
      },
    );
    expect(publishResponse.status()).toBe(200);

    await expect.poll(() => sitemapHasProfile(request, person!.slug)).toBe(true);

    const adminToken = await loginAs(request, accounts.admin);
    const deleteResponse = await request.delete(`${apiUrl}/persons/${person.id}`, {
      headers: authorization(adminToken),
    });
    expect(deleteResponse.status()).toBe(204);
    const deletedSlug = person.slug;
    person = null;

    await expect.poll(() => sitemapHasProfile(request, deletedSlug)).toBe(false);
  } finally {
    if (person) {
      const adminToken = await loginAs(request, accounts.admin);
      const cleanupResponse = await request.delete(`${apiUrl}/persons/${person.id}`, {
        headers: authorization(adminToken),
      });
      expect(cleanupResponse.status()).toBe(204);
    }
  }
});

test("profil osadza jeden bezpieczny i parsowalny blok JSON-LD", async ({ page, request }) => {
  const editorToken = await loginAs(request, accounts.editor);
  const reviewerToken = await loginAs(request, accounts.reviewer);
  const uniqueSuffix = `${Date.now()}-${test.info().workerIndex}`;
  const maliciousSummary =
    `Opis profilu ${uniqueSuffix} </script><script>window.jsonLdProbe=(window.jsonLdProbe||0)+1</script>`;
  let person: CreatedPerson | null = null;

  await page.addInitScript(() => {
    (window as Window & { jsonLdProbe?: number }).jsonLdProbe = 0;
  });

  try {
    const createResponse = await request.post(`${apiUrl}/persons`, {
      headers: authorization(editorToken),
      data: {
        canonical_name: `Św. JSON-LD E2E ${uniqueSuffix}`,
        person_type: "saint",
        status: "draft",
        gender: "unknown",
        summary_pl: maliciousSummary,
        biography_pl: "Profil techniczny do sprawdzenia bezpiecznego JSON-LD.",
      },
    });
    expect(createResponse.status()).toBe(201);
    person = (await createResponse.json()) as CreatedPerson;

    const reviewResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(editorToken),
        data: { target_status: "review", expected_version: 1 },
      },
    );
    expect(reviewResponse.status()).toBe(200);

    const sourceResponse = await request.post(`${apiUrl}/sources/person-links/${person.id}/web`, {
      headers: authorization(editorToken),
      data: {
        title: "Źródło testowego profilu JSON-LD",
        url: `https://example.test/json-ld/${uniqueSuffix}`,
        is_primary: true,
      },
    });
    expect(sourceResponse.status()).toBe(201);

    const publishResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(reviewerToken),
        data: { target_status: "published", expected_version: 3 },
      },
    );
    expect(publishResponse.status()).toBe(200);

    await page.goto(`${webUrl}/swieci/${person.slug}`);
    const jsonLdScript = page.locator('script[type="application/ld+json"]');
    await expect(jsonLdScript).toHaveCount(1);

    const serialized = await jsonLdScript.textContent();
    expect(serialized).toBeTruthy();
    expect(serialized).not.toContain("</script>");
    const parsed = JSON.parse(serialized ?? "null") as {
      "@graph"?: Array<{ description?: string }>;
    };
    expect(parsed["@graph"]?.[0]?.description).toBe(maliciousSummary);
    expect(await page.evaluate(() => (window as Window & { jsonLdProbe?: number }).jsonLdProbe)).toBe(0);
  } finally {
    if (person) {
      const adminToken = await loginAs(request, accounts.admin);
      const cleanupResponse = await request.delete(`${apiUrl}/persons/${person.id}`, {
        headers: authorization(adminToken),
      });
      expect(cleanupResponse.status()).toBe(204);
    }
  }
});
