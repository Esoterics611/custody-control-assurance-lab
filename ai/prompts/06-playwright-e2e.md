# Phase 6 — Playwright E2E (Page Object Model)

package.json + @playwright/test; playwright.config.ts (chromium, baseURL, trace on first
retry, self-starting webServer that boots the API). pages/ConsolePage.ts exposing high-level
actions (submitTransaction, runAssurance, attemptPolicyChange) + accessors — ALL data-testid
selectors live here only. fixtures.ts providing a ready ConsolePage.
Specs: policy-console (allow / over-limit escalation / one-time), screening (sanctioned ->
red BLOCK at screening with alert), assurance-dashboard (12-cell grid all green + coverage),
governance (single admin denied, two admins succeed). No selectors in specs; no sleeps; web-
first assertions. Add an e2e job to CI.

Acceptance: npx playwright test green headless; selectors only in page objects; no sleeps.
