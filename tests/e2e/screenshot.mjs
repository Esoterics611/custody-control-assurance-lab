// Capture demo screenshots for the README.
//   node screenshot.mjs console <baseURL> <out.png>
//   node screenshot.mjs file    <abs-html-path> <out.png>
import { chromium } from "@playwright/test";

const [mode, target, out] = process.argv.slice(2);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });

if (mode === "console") {
  await page.goto(target);
  await page.getByTestId("panel-submit").waitFor();
  // Populate the submit panel with a blocked (sanctioned) transaction.
  await page.getByTestId("preset-sanctioned").click();
  await page.getByTestId("submit-tx").click();
  await page.getByTestId("tx-decision").waitFor();
  // Populate the assurance grid.
  await page.getByTestId("run-assurance").click();
  await page.getByTestId("assurance-cell").first().waitFor();
  await page.screenshot({ path: out, fullPage: true });
} else if (mode === "file") {
  await page.goto("file://" + target);
  await page.screenshot({ path: out, fullPage: true });
} else {
  console.error("unknown mode:", mode);
  process.exit(1);
}

await browser.close();
console.log("wrote", out);
