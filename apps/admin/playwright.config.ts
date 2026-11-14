import { defineConfig, devices } from "@playwright/test";

const adminUrl = process.env.E2E_ADMIN_URL ?? "http://localhost:3000";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

function portFromUrl(value: string, fallback: string): string {
  try {
    return new URL(value).port || fallback;
  } catch {
    return fallback;
  }
}

const adminPort = portFromUrl(adminUrl, "3000");
const webPort = portFromUrl(webUrl, "3001");
const adminDistDir = process.env.E2E_ADMIN_DIST_DIR ?? (process.env.CI ? ".next-e2e-admin" : ".next");
const webDistDir = process.env.E2E_WEB_DIST_DIR ?? (process.env.CI ? ".next-e2e-web" : ".next");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: adminUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `NEXT_DIST_DIR=${adminDistDir} npm run dev -- --hostname localhost --port ${adminPort}`,
      url: adminUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `NEXT_DIST_DIR=${webDistDir} npm --prefix ../web run dev -- --hostname localhost --port ${webPort}`,
      url: webUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
