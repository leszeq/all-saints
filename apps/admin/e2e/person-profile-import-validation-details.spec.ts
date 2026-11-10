import { expect, test } from "@playwright/test";

test("import profilu pokazuje rozwijane szczegóły błędów walidacji", async ({ page }) => {
  const id = "11111111-1111-4111-8111-111111111111";
  const document = {
    schema_version: 1,
    profile: { canonical_name: "Św. Profil z błędem", person_type: "saint" },
    sources: [{ kind: "bibliography", bibliography: { title: "Źródło", description: "Nieobsługiwane" } }],
  };

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    let result: unknown = { items: [], total: 0, pages: 1, queue_counts: { total: 0 }, summary: {} };
    if (url.pathname.endsWith("/auth/refresh")) result = { access_token: "mock-session" };
    if (url.pathname.endsWith("/auth/me")) {
      result = {
        id,
        email: "importer@example.test",
        full_name: "Importer",
        roles: ["admin"],
        permissions: ["persons:read", "import:create"],
        preferred_language: "pl",
      };
    }
    if (url.pathname.endsWith("/persons/import/validate")) {
      const details = [
        {
          field: "body.sources.0.bibliography.description",
          message: "Extra inputs are not permitted",
          type: "extra_forbidden",
        },
      ];
      await route.fulfill({
        status: 422,
        json: {
          error: "VALIDATION_ERROR",
          message: "Dane wejściowe zawierają błędy walidacji",
          detail: details,
          details,
          request_id: "validation-details-test",
        },
      });
      return;
    }
    await route.fulfill({ status: 200, json: result });
  });

  await page.goto("/dashboard/persons");
  await page.getByRole("button", { name: /Import/ }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator('input[type="file"]').setInputFiles({
    name: "profile-with-error.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(document)),
  });

  await expect(dialog.getByText("Sprawdź poprawność wprowadzonych danych.")).toBeVisible();
  const details = dialog.locator("summary").filter({ hasText: "Pokaż szczegóły błędu" });
  await expect(details).toBeVisible();
  await expect(dialog.getByText("sources[0].bibliography.description", { exact: true })).not.toBeVisible();

  await details.click();
  await expect(dialog.getByText("sources[0].bibliography.description", { exact: true })).toBeVisible();
  await expect(
    dialog.getByText(/To pole nie jest obsługiwane w tym miejscu formatu importu/),
  ).toBeVisible();
  await expect(dialog.getByText("Typ walidacji: extra_forbidden", { exact: true })).toBeVisible();
});
