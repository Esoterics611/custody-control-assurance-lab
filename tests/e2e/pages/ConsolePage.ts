import { Page, Locator, expect } from "@playwright/test";

export interface TxParams {
  initiator?: string;
  sourceVault?: string;
  destination: string;
  destinationType: "WHITELISTED" | "ONE_TIME" | "INTERNAL_VAULT" | "UNMANAGED_CONTRACT";
  asset?: string;
  amount: string;
  txType?: "TRANSFER" | "CONTRACT_CALL" | "APPROVE" | "MINT" | "BURN" | "STAKE";
  approvers?: string[];
}

/**
 * Page Object for the security console. ALL selectors (data-testid) live here —
 * spec files never reference a raw selector. Actions use web-first assertions /
 * auto-waiting; there are no hardcoded sleeps.
 */
export class ConsolePage {
  constructor(private readonly page: Page) {}

  async goto(): Promise<void> {
    await this.page.goto("/");
    await expect(this.page.getByTestId("panel-submit")).toBeVisible();
  }

  // --- Submit transaction -------------------------------------------------
  async submitTransaction(params: TxParams): Promise<void> {
    const t = this.page.getByTestId.bind(this.page);
    await t("tx-initiator").fill(params.initiator ?? "dave");
    await t("tx-source-vault").fill(params.sourceVault ?? "1");
    await t("tx-destination").fill(params.destination);
    await t("tx-destination-type").selectOption(params.destinationType);
    await t("tx-type").selectOption(params.txType ?? "TRANSFER");
    await t("tx-asset").fill(params.asset ?? "USDC");
    await t("tx-amount").fill(params.amount);
    await t("tx-approvers").fill((params.approvers ?? []).join(","));
    await t("submit-tx").click();
    // Wait for the result to be populated with a decision.
    await expect(this.txResult()).not.toHaveAttribute("data-decision", "");
  }

  private txResult(): Locator {
    return this.page.getByTestId("tx-result");
  }

  decision(): Locator {
    return this.page.getByTestId("tx-decision");
  }

  async decisionValue(): Promise<string> {
    return (await this.txResult().getAttribute("data-decision")) ?? "";
  }

  async stageValue(): Promise<string> {
    return (await this.txResult().getAttribute("data-stage")) ?? "";
  }

  alerts(): Locator {
    return this.page.getByTestId("tx-alerts");
  }

  // --- Policy change (quorum gate) ---------------------------------------
  async attemptPolicyChange(approvers: string[]): Promise<void> {
    await this.page.getByTestId("policy-approvers").fill(approvers.join(","));
    await this.page.getByTestId("submit-policy-change").click();
    await expect(this.policyResult()).not.toHaveAttribute("data-status", "");
  }

  private policyResult(): Locator {
    return this.page.getByTestId("policy-result");
  }

  async policyStatus(): Promise<string> {
    return (await this.policyResult().getAttribute("data-status")) ?? "";
  }

  policyError(): Locator {
    return this.page.getByTestId("policy-error");
  }

  // --- Assurance dashboard -----------------------------------------------
  async runAssurance(): Promise<void> {
    await this.page.getByTestId("run-assurance").click();
    // The grid is populated asynchronously after the POST resolves.
    await expect(this.controlCells().first()).toBeVisible();
  }

  controlCells(): Locator {
    return this.page.getByTestId("assurance-cell");
  }

  controlCell(controlId: string): Locator {
    return this.page.locator(`[data-testid="assurance-cell"][data-control="${controlId}"]`);
  }

  assuranceSummary(): Locator {
    return this.page.getByTestId("assurance-summary");
  }

  csfCoverage(): Locator {
    return this.page.getByTestId("csf-coverage");
  }

  mitreCoverage(): Locator {
    return this.page.getByTestId("mitre-coverage");
  }
}
