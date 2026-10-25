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
  await openFilters.focus();
  await page.keyboard.press("Enter");

  const drawer = page.getByRole("dialog", { name: "Filtry katalogu" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("checkbox", { name: "Święty/a" })).toBeVisible();
  await expect(drawer.getByRole("button", { name: "Zamknij filtry" })).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(drawer.getByRole("checkbox", { name: "Święty/a" })).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(openFilters).toBeFocused();
});

test("publiczny katalog zachowuje układ przy 200 procentach zoomu", async ({ page }) => {
  // Połowa szerokości desktopowego viewportu odwzorowuje CSS viewport przy 200% zoomu.
  await page.setViewportSize({ width: 640, height: 900 });
  await page.goto(`${webUrl}/swieci`);

  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));

  expect(widths.document).toBeLessThanOrEqual(widths.viewport + 1);
  expect(widths.body).toBeLessThanOrEqual(widths.viewport + 1);
  await expect(page.getByLabel("Szukaj świętego, patronatu lub atrybutu ikonograficznego")).toBeVisible();
});

test("publiczna strona respektuje ograniczenie ruchu", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`${webUrl}/swieci`);

  const motionStyles = await page.evaluate(() => {
    const probe = document.createElement("div");
    probe.className = "transition-colors";
    document.body.appendChild(probe);
    const styles = getComputedStyle(probe);
    const htmlStyles = getComputedStyle(document.documentElement);
    const result = {
      transitionDurationMs: Number.parseFloat(styles.transitionDuration) * (styles.transitionDuration.endsWith("s") ? 1000 : 1),
      scrollBehavior: htmlStyles.scrollBehavior,
    };
    probe.remove();
    return result;
  });

  expect(motionStyles.transitionDurationMs).toBeCloseTo(0.01, 5);
  expect(motionStyles.scrollBehavior).toBe("auto");
});
