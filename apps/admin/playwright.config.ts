import { defineConfig, devices } from "@playwright/test";

const adminUrl = process.env.E2E_ADMIN_URL ?? "http://localhost:3000";
const webUrl = process.env.E2E_WEB_URL ?? "http://localhost:3001";

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
      command: "npm run dev -- --hostname localhost --port 3000",
      url: adminUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm --prefix ../web run dev -- --hostname localhost --port 3001",
      url: webUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
