import { expect, test } from "@playwright/test";

test("nadpisanie profilu wymaga wyboru i ponownej walidacji", async ({ page }) => {
  const id = "11111111-1111-4111-8111-111111111111";
  const profile = { canonical_name: "Św. Rita z Cascii", summary_pl: "Nowy biogram", person_type: "saint" };
  const document = { schema_version: 1, profile, feasts: [{ calendar_code: "roman_universal", month: 5, day: 22, is_primary: true }] };
  let overwriteRequests = 0;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let result: unknown = { items: [], total: 0, pages: 1, queue_counts: { total: 0 }, summary: {} };
    if (url.pathname.endsWith("/auth/refresh")) result = { access_token: "mock-session" };
    if (url.pathname.endsWith("/auth/me")) result = {
      id, email: "importer@example.test", full_name: "Importer", roles: ["admin"],
      permissions: ["persons:read", "persons:update", "persons:publish", "import:create"], preferred_language: "pl",
    };
    if (url.pathname.endsWith("/persons/import/validate")) {
      const overwrite = url.searchParams.get("overwrite_person_id") === id;
      if (overwrite) expect(url.searchParams.get("expected_version")).toBe("7");
      result = {
        can_import: overwrite,
        existing_person: { id, canonical_name: profile.canonical_name, slug: "sw-rita-z-cascii", status: "published", version: 7 },
        errors: overwrite ? [] : ["Aktywny profil o tej samej nazwie kanonicznej już istnieje."],
        warnings: overwrite ? [] : ["W kalendarzu jest już główny wpis."],
        normalized_document: { ...document, feasts: [{ ...document.feasts[0], is_primary: overwrite }] },
      };
    }
    if (url.pathname.endsWith("/persons/import")) {
      overwriteRequests += 1;
      expect(url.searchParams.get("overwrite_person_id")).toBe(id);
      expect(url.searchParams.get("expected_version")).toBe("7");
      // Submit the original file, not the primary flag downgraded by create validation.
      expect(request.postDataJSON()).toEqual(document);
      result = { ...profile, id, slug: "sw-rita-z-cascii", status: "published", version: 9 };
    }
    await route.fulfill({ status: 200, json: result });
  });
  await page.goto("/dashboard/persons");
  await page.getByRole("button", { name: /Import/ }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator('input[type="file"]').setInputFiles({
    name: "sw-rita-z-cascii.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(document)),
  });
  await expect(dialog.getByText("Aktywny profil o tej samej nazwie kanonicznej już istnieje.")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Dodaj jako szkic" })).toBeDisabled();
  const consent = dialog.getByRole("checkbox", { name: "Chcę nadpisać istniejący profil danymi z pliku" });
  await expect(consent).not.toBeChecked();
  await expect(dialog.getByText(/Zapisane zmiany będą od razu publiczne/)).toBeVisible();
  await consent.check();
  await expect(dialog.getByRole("button", { name: "Nadpisz istniejący profil" })).toBeEnabled();
  await expect(dialog.getByText("Aktywny profil o tej samej nazwie kanonicznej już istnieje.")).not.toBeVisible();
  await consent.uncheck();
  await expect(dialog.getByRole("button", { name: "Dodaj jako szkic" })).toBeDisabled();
  await expect(consent).toBeEnabled();
  expect(overwriteRequests).toBe(0);
  await consent.check();
  await dialog.getByRole("button", { name: "Nadpisz istniejący profil" }).click();
  await expect(page).toHaveURL(`/dashboard/persons/${id}`);
  expect(overwriteRequests).toBe(1);
});
