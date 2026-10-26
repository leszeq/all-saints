import { expect, test } from "@playwright/test";

const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

declare global {
  interface Window {
    __captureAnalyticsBeacon?: (url: string, body: string) => void;
  }
}

test("wyszukiwanie emituje jedno zdarzenie bez treści zapytania", async ({ page }) => {
  const events: Array<Record<string, unknown>> = [];
  await page.exposeFunction("__captureAnalyticsBeacon", (url: string, body: string) => {
    if (!url.includes("/api/v1/events")) return;
    const payload = JSON.parse(body) as Record<string, unknown>;
    if (payload.event_name === "search_submitted") events.push(payload);
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

  await expect.poll(() => events.length).toBe(1);

  const event = events[0];
  expect(event).toMatchObject({ event_name: "search_submitted", query_class: "name" });
  expect(event).not.toHaveProperty("query");
  expect(event).not.toHaveProperty("search");
});
