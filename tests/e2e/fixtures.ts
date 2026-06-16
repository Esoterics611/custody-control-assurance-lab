import { test as base } from "@playwright/test";
import { ConsolePage } from "./pages/ConsolePage";

/** Provides a ConsolePage already navigated to the console and ready to drive. */
export const test = base.extend<{ console: ConsolePage }>({
  console: async ({ page }, use) => {
    // Reset the shared in-memory platform so each test starts from the reference
    // config (the suite runs serially — see workers:1 in playwright.config.ts).
    await page.request.post("/admin/reset");
    const console = new ConsolePage(page);
    await console.goto();
    await use(console);
  },
});

export { expect } from "@playwright/test";
