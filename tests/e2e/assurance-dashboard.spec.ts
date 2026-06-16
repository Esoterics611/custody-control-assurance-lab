import { test, expect } from "./fixtures";

test.describe("Control assurance dashboard", () => {
  test("running assurance renders a 16-control grid with coverage", async ({ console }) => {
    await console.runAssurance();

    await expect(console.controlCells()).toHaveCount(16);
    await expect(console.csfCoverage()).toContainText("PR.AA");
    await expect(console.mitreCoverage()).toContainText("T1657");
  });

  test("every control cell is green (pass) in the reference config", async ({ console }) => {
    await console.runAssurance();

    const cells = console.controlCells();
    const count = await cells.count();
    expect(count).toBe(16);
    for (let i = 0; i < count; i++) {
      await expect(cells.nth(i)).toHaveAttribute("data-state", "pass");
    }
    await expect(console.assuranceSummary()).toHaveAttribute("data-all-passed", "true");
  });

  test("a specific control (C-07 sanctions) is present and passing", async ({ console }) => {
    await console.runAssurance();
    await expect(console.controlCell("C-07")).toHaveAttribute("data-state", "pass");
  });
});
