import { expect, test } from "@playwright/test";

const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

declare global {
  interface Window {
    __captureAnalyticsBeacon?: (url: string, body: string) => void;
  }
}

test("funnel wyszukiwanie → profil → źródło emituje zdarzenia bez danych surowych", async ({ page }) => {
  const events: Array<Record<string, unknown>> = [];
  await page.exposeFunction("__captureAnalyticsBeacon", (url: string, body: string) => {
    if (!url.includes("/api/v1/events")) return;
    const payload = JSON.parse(body) as Record<string, unknown>;
    events.push(payload);
  });
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: (url: string, data: Blob | null = null) => {
        if (data instanceof Blob) {
          void data.text().then((body) => window.__captureAnalyticsBeacon?.(url, body));
        } else {
          window.__captureAnalyticsBeacon?.(url, "{}");
        }
        return true;
      },
    });
  });

  await page.goto(`${webUrl}/swieci`);
  await page.getByRole("textbox", { name: "Szukaj świętego, patronatu lub atrybutu ikonograficznego" }).fill("Jan");
  await page.getByRole("button", { name: "Filtruj" }).click();

  const searchEvent = () => events.find((event) => event.event_name === "search_submitted");
  await expect.poll(searchEvent).toBeTruthy();
  const profileLink = page.locator('a[href^="/swieci/"]').first();
  await expect(profileLink).toBeVisible();
  await profileLink.click();
  await expect(page).toHaveURL(/\/swieci\/[^/?#]+$/);
  await expect.poll(() => events.filter((event) => event.event_name === "profile_opened").length).toBe(1);

  const sourceLink = page.locator("#bibliografia a[data-analytics-source-kind]").first();
  await expect(sourceLink).toBeVisible();
  await sourceLink.dispatchEvent("click");
  await expect.poll(() => events.filter((event) => event.event_name === "source_opened").length).toBe(1);

  const event = searchEvent();
  expect(event).toMatchObject({ event_name: "search_submitted", query_class: "name" });
  expect(event).not.toHaveProperty("query");
  expect(event).not.toHaveProperty("search");
});
