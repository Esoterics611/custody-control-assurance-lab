import { test, expect } from "./fixtures";

const SANCTIONED = "0xSANCTIONED00000000000000000000000000000001";

test.describe("Compliance screening in the console", () => {
  test("a sanctioned destination is BLOCKed at screening with an alert", async ({ console }) => {
    await console.submitTransaction({
      destination: SANCTIONED,
      destinationType: "WHITELISTED",
      amount: "5000",
    });

    expect(await console.decisionValue()).toBe("BLOCK");
    expect(await console.stageValue()).toBe("screening");
    await expect(console.decision()).toHaveText("BLOCK");
    await expect(console.alerts()).toContainText("SCREENING ALERT");
    await expect(console.alerts()).toContainText("OFAC_SANCTION");
  });
});
