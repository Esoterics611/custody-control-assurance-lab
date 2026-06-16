import { test, expect } from "./fixtures";

test.describe("Admin-quorum governance gate", () => {
  test("a single-admin policy change is denied with the quorum message", async ({ console }) => {
    await console.attemptPolicyChange(["alice"]);

    expect(await console.policyStatus()).toBe("denied");
    await expect(console.policyError()).toContainText("admin approvals");
  });

  test("two distinct admins can apply a policy change", async ({ console }) => {
    await console.attemptPolicyChange(["alice", "bob"]);
    expect(await console.policyStatus()).toBe("applied");
  });
});
