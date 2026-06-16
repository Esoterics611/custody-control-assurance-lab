import { test, expect } from "./fixtures";

const CLEAN = "0xCLEAN0000000000000000000000000000000000099";
const EXTERNAL = "0xEXTERNAL0000000000000000000000000000000777";

test.describe("TAP policy decisions in the console", () => {
  test("whitelisted under-limit transfer is ALLOWed", async ({ console }) => {
    await console.submitTransaction({
      destination: CLEAN,
      destinationType: "WHITELISTED",
      amount: "5000",
    });
    expect(await console.decisionValue()).toBe("ALLOW");
    await expect(console.decision()).toHaveText("ALLOW");
  });

  test("over-limit transfer is escalated to REQUIRE_APPROVAL", async ({ console }) => {
    await console.submitTransaction({
      destination: CLEAN,
      destinationType: "WHITELISTED",
      amount: "250000",
    });
    expect(await console.decisionValue()).toBe("REQUIRE_APPROVAL");
    expect(await console.stageValue()).toBe("approval");
  });

  test("large one-time destination is escalated", async ({ console }) => {
    await console.submitTransaction({
      destination: EXTERNAL,
      destinationType: "ONE_TIME",
      amount: "15000",
    });
    expect(await console.decisionValue()).toBe("REQUIRE_APPROVAL");
  });
});
