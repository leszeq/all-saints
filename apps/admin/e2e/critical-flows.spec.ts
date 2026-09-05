import { expect, test, type APIRequestContext } from "@playwright/test";

const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";
const password = process.env.E2E_PASSWORD ?? "DemoE2E123!";

const accounts = {
  admin: process.env.E2E_ADMIN_EMAIL ?? "admin.test@encyklopedia.pl",
  editor: process.env.E2E_EDITOR_EMAIL ?? "redaktor.test@encyklopedia.pl",
  reviewer: process.env.E2E_REVIEWER_EMAIL ?? "recenzent.test@encyklopedia.pl",
};

type LoginResponse = {
  access_token: string;
};

type CreatedPerson = {
  id: string;
  slug: string;
  canonical_name: string;
};

async function loginAs(request: APIRequestContext, email: string) {
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

test("redaktor loguje się do panelu administracyjnego", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Adres e-mail").fill(accounts.editor);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "Zaloguj się" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Pulpit redakcyjny" })).toBeVisible();
});

test("szkic staje się publiczny dopiero po pełnym workflow", async ({ page, request }) => {
  const editorToken = await loginAs(request, accounts.editor);
  const reviewerToken = await loginAs(request, accounts.reviewer);
  const uniqueSuffix = `${Date.now()}-${test.info().workerIndex}`;
  let person: CreatedPerson | null = null;

  try {
    const createResponse = await request.post(`${apiUrl}/persons`, {
      headers: authorization(editorToken),
      data: {
        canonical_name: `Św. Test E2E ${uniqueSuffix}`,
        person_type: "saint",
        status: "draft",
        gender: "unknown",
        summary_pl: "Zweryfikowane streszczenie testowego rekordu end-to-end.",
        biography_pl: "Zweryfikowany biogram testowego rekordu end-to-end.",
      },
    });
    expect(createResponse.status()).toBe(201);
    person = (await createResponse.json()) as CreatedPerson;

    const hiddenApiResponse = await request.get(`${apiUrl}/persons/${person.slug}`);
    expect(hiddenApiResponse.status()).toBe(404);

    await page.goto(`${webUrl}/swieci/${person.slug}`);
    await expect(page.getByRole("heading", { name: "Nie znaleziono strony" })).toBeVisible();

    const reviewResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(editorToken),
        data: { target_status: "review", expected_version: 1 },
      },
    );
    expect(reviewResponse.status()).toBe(200);
    expect((await reviewResponse.json()).status).toBe("review");

    const publishResponse = await request.post(
      `${apiUrl}/editorial/queue/${person.id}/transition`,
      {
        headers: authorization(reviewerToken),
        data: { target_status: "published", expected_version: 2 },
      },
    );
    expect(publishResponse.status()).toBe(200);
    expect((await publishResponse.json()).status).toBe("published");

    const publishedPageResponse = await page.goto(`${webUrl}/swieci/${person.slug}`);
    expect(publishedPageResponse?.status()).toBe(200);
    await expect(page.getByRole("heading", { name: person.canonical_name })).toBeVisible();
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

test("redaktor może przesłać obraz, a zapisany plik jest dostępny", async ({ request }) => {
  const editorToken = await loginAs(request, accounts.editor);
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );

  const uploadResponse = await request.post(`${apiUrl}/sources/images/upload`, {
    headers: authorization(editorToken),
    multipart: {
      file: {
        name: "avatar-e2e.png",
        mimeType: "image/png",
        buffer: png,
      },
    },
  });

  expect(uploadResponse.status()).toBe(201);
  const uploaded = (await uploadResponse.json()) as {
    url: string;
    thumbnail_url: string;
    mime_type: string;
    width_px: number;
    height_px: number;
  };
  expect(uploaded).toMatchObject({
    mime_type: "image/webp",
    width_px: 1,
    height_px: 1,
  });

  for (const imageUrl of [uploaded.url, uploaded.thumbnail_url]) {
    const imageResponse = await request.get(imageUrl);
    expect(imageResponse.status()).toBe(200);
    expect(imageResponse.headers()["content-type"]).toContain("image/webp");
    expect((await imageResponse.body()).byteLength).toBeGreaterThan(0);
  }
});
