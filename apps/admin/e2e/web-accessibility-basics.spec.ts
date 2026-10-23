import { expect, test } from "@playwright/test";

const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

test("publiczna strona ma skip link i jeden landmark main", async ({ page }) => {
  await page.goto(`${webUrl}/swieci`);

  const skipLink = page.getByRole("link", { name: "Przejdź do treści" });
  await expect(skipLink).toHaveAttribute("href", "#main-content");
  await skipLink.focus();
  await expect(skipLink).toBeVisible();

  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.locator("#main-content")).toHaveCount(1);
  await expect(page.getByLabel("Szukaj świętego, patronatu lub atrybutu ikonograficznego")).toHaveAttribute(
    "id",
    "saints-search",
  );

  const saintFilter = page.getByRole("checkbox", { name: "Święty/a" });
  await saintFilter.focus();
  await expect(saintFilter).toBeFocused();
  await expect(saintFilter.locator("xpath=following-sibling::span")).toHaveClass(
    /peer-focus-visible:outline/,
  );
});

test("mobilny katalog otwiera i zamyka drawer filtrów", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${webUrl}/swieci`);

  const openFilters = page.getByRole("button", { name: "Filtry katalogu" });
  await expect(openFilters).toBeVisible();
  await openFilters.click();

  const drawer = page.getByRole("dialog", { name: "Filtry katalogu" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("checkbox", { name: "Święty/a" })).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(openFilters).toBeFocused();
});
