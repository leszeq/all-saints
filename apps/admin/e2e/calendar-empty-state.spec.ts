import { expect, test } from "@playwright/test";

const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000/api/v1";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

test("pusty dzień kalendarza ma komunikat o braku opracowania", async ({ page, request }) => {
  const year = new Date().getUTCFullYear();
  const monthResponse = await request.get(
    `${apiUrl}/calendar/month/${year}/2?calendar_code=roman_pl&include_universal=true&include_martyrology=true`,
  );
  expect(monthResponse.ok()).toBeTruthy();

  const month = (await monthResponse.json()) as {
    days: Array<{ date: string; entries: unknown[] }>;
  };
  const emptyDay = month.days.find((day) => day.entries.length === 0);
  expect(emptyDay, "Kalendarz testowy musi zawierać pusty dzień").toBeTruthy();
  if (!emptyDay) return;

  const pageResponse = await page.goto(
    `${webUrl}/kalendarz/${emptyDay.date}?calendar=roman_pl`,
  );
  expect(pageResponse?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Dzień czeka na opracowanie" })).toBeVisible();
  await expect(
    page.getByText("W bazie nie ma jeszcze zweryfikowanych wpisów przypisanych do tej daty.", {
      exact: false,
    }),
  ).toBeVisible();

  const mainText = (await page.getByRole("main").last().innerText()).toLocaleLowerCase("pl-PL");
  expect(mainText).not.toContain("nikt");
});
