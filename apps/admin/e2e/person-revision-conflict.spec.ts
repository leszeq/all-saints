import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const personId = "22222222-2222-4222-8222-222222222222";
const revisionId = "33333333-3333-4333-8333-333333333333";
const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";

type RevisionFixture = {
  id: string;
  person_id: string;
  revision_number: number;
  status: "draft" | "review" | "published";
  base_version: number;
  base_revision_id: string | null;
  payload: Record<string, unknown>;
  author_id: string | null;
  change_summary: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

type RevisionApiState = {
  person: ReturnType<typeof personFixture>;
  revision: RevisionFixture;
  successfulUpdates: number;
  successfulPublishes: number;
};

function personFixture() {
  return {
    id: personId,
    slug: "sw-test-konflikt-rewizji",
    canonical_name: "Św. Test konfliktu rewizji",
    canonical_name_en: null,
    latin_name: null,
    person_type: "saint",
    status: "published",
    gender: "unknown",
    era: "modern",
    birth_year: null,
    death_year: null,
    birth_country_id: null,
    death_country_id: null,
    state_of_life_id: null,
    summary_pl: "Bazowe streszczenie",
    biography_pl: "Bazowy biogram",
    prayers: null,
    iconographic_attributes: null,
    aliases: [],
    patronages: [],
    avatar: null,
    beatification: null,
    canonization: null,
    version: 7,
  };
}

function revisionFixture(): RevisionFixture {
  const now = "2026-11-13T12:00:00Z";
  return {
    id: revisionId,
    person_id: personId,
    revision_number: 1,
    status: "draft",
    base_version: 7,
    base_revision_id: null,
    payload: {
      ...personFixture(),
      summary_pl: "Bazowe streszczenie",
      biography_pl: "Bazowy biogram",
    },
    author_id: null,
    change_summary: null,
    version: 1,
    created_at: now,
    updated_at: now,
  };
}

function createRevisionApiState(): RevisionApiState {
  return {
    person: personFixture(),
    revision: revisionFixture(),
    successfulUpdates: 0,
    successfulPublishes: 0,
  };
}

async function mockRevisionApi(context: BrowserContext, state: RevisionApiState) {
  const { person, revision } = state;

  await context.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const json = (status: number, body: unknown) => route.fulfill({ status, json: body });
    const user = {
      id: "44444444-4444-4444-8444-444444444444",
      email: "redaktor-konflikt@example.test",
      full_name: "Redaktor konfliktu",
      roles: ["admin"],
      permissions: ["persons:read", "persons:update", "persons:submit", "persons:review"],
      preferred_language: "pl",
    };

    if (path.endsWith("/auth/refresh")) return json(200, { access_token: "mock-conflict-session" });
    if (path.endsWith("/auth/me")) return json(200, user);
    if (method === "GET" && path.endsWith("/editorial/dashboard")) {
      return json(200, {
        generated_at: "2026-11-13T12:00:00Z",
        total_persons: 1,
        status_counts: [],
        attention_count: 0,
        unknown_license_images: 0,
        completion: [],
        monthly_activity: [],
        recent_records: [],
        queue_preview: [],
        queue_counts: { total: 0, draft: 0, review: 0, attention: 0, urgent: 0, high: 0, normal: 0 },
        resources: { users: 1, countries: 0, orders: 0, bibliography: 0 },
      });
    }
    if (method === "GET" && path.endsWith("/editorial/quality")) {
      return json(200, {
        generated_at: "2026-11-13T12:00:00Z",
        summary: {
          records_with_issues: 0,
          total_issues: 0,
          duplicate_groups: 0,
          duplicate_records: 0,
          source_items_to_review: 0,
          bibliography_sources: 0,
          historical_sources: 0,
          person_source_links: 0,
          documented_persons: 0,
          undocumented_persons: 0,
          unknown_license_images: 0,
        },
        issue_breakdown: [],
        problem_records: [],
        duplicate_groups: [],
        source_stats: {
          bibliography_sources: 0,
          historical_sources: 0,
          person_source_links: 0,
          documented_persons: 0,
          undocumented_persons: 0,
          images: 0,
          unknown_license_images: 0,
        },
        source_verification_items: [],
      });
    }
    if (method === "GET" && path.endsWith("/ai/suggestions")) {
      return json(200, { items: [], total: 0, pending_review: 0, ready_to_generate: 0, blocked: 0 });
    }
    if (method === "GET" && path.endsWith(`/persons/admin/${personId}`)) return json(200, person);
    if (method === "GET" && path.endsWith(`/persons/${personId}/revisions/active`)) return json(200, revision);
    if (method === "GET" && path.endsWith(`/calendar/persons/${personId}/entries`)) {
      return json(200, [{
        id: "55555555-5555-4555-8555-555555555555",
        month: 11,
        day: 1,
        rank: "solemnity",
        liturgical_color: "white",
        is_primary: true,
        source_title: "Kalendarz Polski",
        source_url: null,
        notes: null,
        calendar: { code: "roman_pl", name: "Kalendarz Polski" },
      }]);
    }
    if (method === "GET" && path.endsWith("/geography/countries")) return json(200, []);
    if (method === "GET" && path.endsWith("/taxonomy/states-of-life")) return json(200, []);
    if (method === "GET" && path.endsWith("/calendar/calendars")) return json(200, []);

    if (method === "PATCH" && path.endsWith(`/revisions/${revisionId}`)) {
      const body = request.postDataJSON() as { expected_version: number; changes: Record<string, unknown> };
      if (body.expected_version !== revision.version) {
        return json(409, {
          detail: {
            message: `Rewizja ma już wersję ${revision.version}, a formularz wersję ${body.expected_version}.`,
            code: "publication_revision_version_conflict",
            expected_version: body.expected_version,
            current_version: revision.version,
          },
        });
      }
      revision.payload = { ...revision.payload, ...body.changes };
      revision.version += 1;
      revision.updated_at = "2026-11-13T12:01:00Z";
      state.successfulUpdates += 1;
      return json(200, revision);
    }

    if (method === "POST" && path.endsWith(`/revisions/${revisionId}/submit`)) {
      const body = request.postDataJSON() as { expected_version: number };
      if (body.expected_version !== revision.version) {
        return json(409, {
          detail: {
            message: "Rewizja ma nowszą wersję.",
            code: "publication_revision_version_conflict",
            expected_version: body.expected_version,
            current_version: revision.version,
          },
        });
      }
      revision.status = "review";
      revision.version += 1;
      return json(200, revision);
    }

    if (method === "POST" && path.endsWith(`/revisions/${revisionId}/publish`)) {
      const body = request.postDataJSON() as { expected_version: number };
      if (body.expected_version !== revision.version) {
        return json(409, {
          detail: {
            message: "Rewizja ma nowszą wersję.",
            code: "publication_revision_version_conflict",
            expected_version: body.expected_version,
            current_version: revision.version,
          },
        });
      }
      revision.status = "published";
      revision.version += 1;
      person.version += 1;
      person.summary_pl = String(revision.payload.summary_pl ?? person.summary_pl);
      state.successfulPublishes += 1;
      return json(200, revision);
    }

    return json(200, { items: [], total: 0, pages: 1 });
  });

  return {
    get successfulUpdates() {
      return state.successfulUpdates;
    },
    get successfulPublishes() {
      return state.successfulPublishes;
    },
    revision,
  };
}

async function openEditor(page: Page) {
  await page.goto(`/dashboard/persons/${personId}/edit`);
  await expect(page.getByRole("button", { name: "Zapisz szkic rewizji" })).toBeVisible();
  await page.getByRole("button", { name: "Biografia" }).click();
}

async function runWorkflow(page: Page) {
  return page.evaluate(async ({ baseUrl, id }) => {
    const headers = { "Content-Type": "application/json" };
    const submit = await fetch(`${baseUrl}/revisions/${id}/submit`, {
      method: "POST",
      headers,
      body: JSON.stringify({ expected_version: 2 }),
    });
    if (!submit.ok) throw new Error(`submit failed: ${submit.status}`);
    const reviewed = await submit.json() as { version: number };
    const publish = await fetch(`${baseUrl}/revisions/${id}/publish`, {
      method: "POST",
      headers,
      body: JSON.stringify({ expected_version: reviewed.version }),
    });
    if (!publish.ok) throw new Error(`publish failed: ${publish.status}`);
    return publish.json();
  }, { baseUrl: apiUrl, id: revisionId });
}

test("dwie osoby edytują jedną rewizję, a zwycięska wersja może zostać opublikowana", async ({ browser }) => {
  const firstContext = await browser.newContext();
  const secondContext = await browser.newContext();
  const firstPage = await firstContext.newPage();
  const secondPage = await secondContext.newPage();
  const state = createRevisionApiState();
  const firstState = await mockRevisionApi(firstContext, state);
  await mockRevisionApi(secondContext, state);

  try {
    await Promise.all([openEditor(firstPage), openEditor(secondPage)]);

    const firstSummary = firstPage.locator("#person-field-summary_pl");
    const secondSummary = secondPage.locator("#person-field-summary_pl");
    await firstSummary.fill("Zmiana redaktora A");
    await secondSummary.fill("Zmiana redaktora B");

    await firstPage.getByRole("button", { name: "Zapisz szkic rewizji" }).click();
    await expect.poll(() => firstState.successfulUpdates).toBe(1);

    await secondPage.getByRole("button", { name: "Zapisz szkic rewizji" }).click();
    await expect(secondPage.getByRole("heading", { name: "Rekord zmienił się podczas edycji" })).toBeVisible();
    await expect(secondSummary).toHaveValue("Zmiana redaktora B");

    await secondPage.getByRole("button", { name: "Pokaż różnice" }).click();
    await expect(secondPage.getByText("summary_pl", { exact: true })).toBeVisible();
    await expect(secondPage.getByText("Zmiana redaktora B", { exact: true })).toBeVisible();
    await expect(secondPage.getByText("Zmiana redaktora A", { exact: true })).toBeVisible();

    await runWorkflow(firstPage);
    expect(firstState.successfulPublishes).toBe(1);
    expect(state.successfulPublishes).toBe(1);
    expect(firstState.revision.status).toBe("published");
    expect(firstState.revision.payload.summary_pl).toBe("Zmiana redaktora A");
  } finally {
    await firstContext.close();
    await secondContext.close();
  }
});
