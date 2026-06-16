import { defineConfig, devices } from "@playwright/test";

const PORT = process.env.CAL_PORT ?? "8071";
const BASE_URL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: ".",
  // The suite drives ONE shared in-memory platform; run serially and reset per
  // test (see fixtures.ts) so state never leaks between specs.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "list" : [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Self-starting: boot the API + console from the repo root via uv.
  webServer: {
    command: "cd ../.. && uv run python -m cal.api.serve",
    url: `${BASE_URL}/healthz`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { CAL_HOST: "127.0.0.1", CAL_PORT: PORT },
  },
});
