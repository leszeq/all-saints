import axe from "axe-core";
import { expect, test, type Page } from "@playwright/test";

const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

async function expectAccessible(page: Page, label: string) {
  await page.addScriptTag({ content: axe.source });
  const violations = await page.evaluate(async () => {
    const axeGlobal = (window as unknown as Window & {
      axe: {
        run: (
          context: Document,
          options: { runOnly: { type: "tag"; values: string[] } },
        ) => Promise<{ violations: Array<{ id: string; help: string; nodes: Array<{ target: string[] }> }> }>;
      };
    }).axe;
    const results = await axeGlobal.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa"] },
    });
    return results.violations.map(({ id, help, nodes }) => ({
      id,
      help,
      nodeCount: nodes.length,
      targets: nodes.map((node) => node.target),
    }));
  });

  expect(violations, `${label} ma naruszenia WCAG`).toEqual([]);
}

test("web: katalog publiczny przechodzi smoke accessibility", async ({ page }) => {
  await page.goto(`${webUrl}/swieci`);
  await expectAccessible(page, "Publiczny katalog");
});

test("admin: logowanie przechodzi smoke accessibility", async ({ page }) => {
  await page.goto("/login");
  await expectAccessible(page, "Logowanie admina");
});
