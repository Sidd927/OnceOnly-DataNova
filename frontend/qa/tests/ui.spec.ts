import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Interaction coverage for the redesigned frontend, against the live, seeded stack
 * (`make chain deploy api web seed`). Read-only except for verification uploads.
 */
const DEMO = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "data", "demo");

async function claimId(page: Page, claimant: string) {
  const claims = await (await page.request.get("/api/claims")).json();
  const c = claims.find((x: any) => x.claimant.startsWith(claimant));
  expect(c, `seeded claim for ${claimant}`).toBeTruthy();
  return c as { id: number; ref: string };
}

test.describe("landing", () => {
  test("hero is readable immediately and, with reduced motion, shows the final overlap state", async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Every retired tonne, claimed once.");
    await expect(page.getByText("Rejected by contract").first()).toBeVisible();
    await expect(page.getByText("4,559 units claimed twice").first()).toBeVisible();
    await ctx.close();
  });

  test("hero steps are buttons that change the explanation", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Step 1: Retirement" }).click();
    await expect(page.getByText(/Verra records 19,999 units/)).toBeVisible();
    await page.getByRole("button", { name: "Step 4: Overlap" }).click();
    await expect(page.getByText(/the contract refuses the second registration/)).toBeVisible();
    // the illustration links to the real rejected transaction in the seeded ledger
    await page.getByRole("link", { name: /See this rejection as a real transaction/ }).click();
    await expect(page.getByText("Rejected by contract").first()).toBeVisible();
    await expect(page.getByText(/Failed transaction/).first()).toBeVisible();
  });

  test("How it works scrolls to the mechanism section", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "How it works" }).first().click();
    await expect(page.getByRole("heading", { name: "A claim is an interval." })).toBeInViewport();
  });

  test("serial anatomy explains the selected segment", async ({ page }) => {
    await page.goto("/#how");
    await page.getByRole("button", { name: "Last unit: 896319559" }).click();
    await expect(page.getByText(/Range size: 10,000 units/)).toBeVisible();
  });
});

test.describe("signature: first viewport and the Ruler", () => {
  for (const vp of [{ width: 1280, height: 800 }, { width: 390, height: 844 }]) {
    test(`overlap annotation is visible without scrolling at ${vp.width}x${vp.height}`, async ({ browser }) => {
      const ctx = await browser.newContext({ viewport: vp, reducedMotion: "reduce" });
      const page = await ctx.newPage();
      await page.goto("/");
      await expect(page.getByText("4,559 units claimed twice", { exact: true }).first()).toBeInViewport();
      await expect(page.getByText("896,315,001", { exact: true }).first()).toBeInViewport();
      await ctx.close();
    });
  }

  test("selecting an overlap highlights it on both lanes; exact boundaries are on the scale", async ({ page }) => {
    const claims = await (await page.request.get("/api/claims")).json();
    const helios = claims.find((x: any) => x.claimant.startsWith("Helios"));
    await page.goto(`/claims/${helios.id}`);
    const overlaps = page.getByRole("button", { name: /^Overlap: 4,559 units/ });
    await expect(overlaps).toHaveCount(2); // one on the other claim's lane, one on this claim's lane
    await overlaps.first().click();
    for (const el of await overlaps.all()) await expect(el).toHaveCSS("outline-style", "solid");
    await expect(page.getByText("896,319,559", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/does not say which claim is right/)).toBeVisible();
  });
});

test.describe("claims ledger", () => {
  test("filter, search and sort operate on real rows", async ({ page }) => {
    await page.goto("/claims");
    const rows = page.locator("table tbody tr");
    await expect(rows.first()).toBeVisible();
    const total = await rows.count();
    expect(total).toBeGreaterThanOrEqual(5);
    const chip = page.getByRole("button", { name: /^Blocked/ });
    const blockedCount = Number((await chip.textContent())!.replace(/\D/g, ""));
    await chip.click();
    await expect(page).toHaveURL(/status=blocked/);
    await expect(chip).toHaveAttribute("aria-pressed", "true");
    await expect(rows).toHaveCount(blockedCount);
    for (const r of await rows.all()) await expect(r.getByText("Blocked", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /^All/ }).click();
    await page.getByRole("searchbox", { name: "Search claims" }).fill("helios");
    await expect(rows).toHaveCount(1);
    await page.getByRole("searchbox", { name: "Search claims" }).fill("");
    const unitsHeader = page.getByRole("columnheader", { name: /Units/ });
    await unitsHeader.getByRole("button").click();
    await expect(unitsHeader).toHaveAttribute("aria-sort", "descending");
    await unitsHeader.getByRole("button").click();
    await expect(unitsHeader).toHaveAttribute("aria-sort", "ascending");
  });
});

test.describe("claim detail", () => {
  test("overlap is shown on the ruler, selectable by keyboard, and linked to the other claim", async ({ page }) => {
    const helios = await claimId(page, "Helios");
    await page.goto(`/claims/${helios.id}`);
    await expect(page.getByText(/4,559 units already back/)).toBeVisible();
    const overlap = page.getByRole("button", { name: /Overlap: 4,559 units/ }).first();
    await expect(overlap).toBeVisible();
    // keyboard: focusing a band updates the live readout
    const registryBand = page.getByRole("button", { name: /^Registry: Retired/ }).first();
    await registryBand.focus();
    await expect(page.getByText(/no beneficiary recorded · Berkeley VROD/).first()).toBeVisible();
    await overlap.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("link", { name: /Open Northwind Foods/ })).toBeVisible();
    // accessible table alternative
    await page.getByRole("button", { name: "Show ranges as a table" }).first().click();
    await expect(page.getByRole("rowheader", { name: "Claimed twice" })).toBeVisible();
  });

  test("anchoring is disabled with a reason and the forced attempt asks for confirmation (Esc cancels)", async ({ page }) => {
    const helios = await claimId(page, "Helios");
    await page.goto(`/claims/${helios.id}`);
    await expect(page.getByRole("button", { name: "Anchor on ledger" }).first()).toBeDisabled();
    await expect(page.getByText(/Disabled because of the blocking finding/).filter({ visible: true })).toBeVisible();
    if ((await (await page.request.get("/api/health")).json()).public_demo) {
      // public demo instance: ledger writes are refused server-side and the controls say why
      await expect(page.getByRole("button", { name: "Send to the contract anyway" }).filter({ visible: true })).toBeDisabled();
      await expect(page.getByText(/Public demo instance\./).filter({ visible: true })).toBeVisible();
      return;
    }
    await page.getByRole("button", { name: "Send to the contract anyway" }).click();
    const dialog = page.getByRole("dialog", { name: /Send a registration the contract should reject/ });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Cancel" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("a claim without serials explains insufficient evidence", async ({ page }) => {
    const k = await claimId(page, "Kestrel");
    await page.goto(`/claims/${k.id}`);
    await expect(page.getByText(/No serial numbers were disclosed/)).toBeVisible();
    await expect(page.getByText("Insufficient evidence").first()).toBeVisible();
  });
});

test.describe("verify", () => {
  test("matching and tampered documents produce different outcomes", async ({ page }) => {
    const nw = await claimId(page, "Northwind");
    const original = readFileSync(join(DEMO, "northwind_allocation.pdf"));
    await page.goto(`/verify?ref=${nw.ref}`);
    await page.locator('input[type="file"]').setInputFiles({ name: "northwind.pdf", mimeType: "application/pdf", buffer: original });
    await page.getByRole("button", { name: "Verify", exact: true }).click();
    await expect(page.getByText("Fingerprint matches")).toBeVisible();
    const tampered = Buffer.concat([original, Buffer.from(" ")]);
    await page.getByRole("button", { name: /Remove northwind.pdf/ }).click();
    await page.locator('input[type="file"]').setInputFiles({ name: "northwind-edited.pdf", mimeType: "application/pdf", buffer: tampered });
    await page.getByRole("button", { name: "Verify", exact: true }).click();
    await expect(page.getByText("Fingerprint differs")).toBeVisible();
  });

  test("unknown reference is reported as not on the ledger", async ({ page }) => {
    await page.goto("/verify");
    await page.getByRole("textbox", { name: "Claim reference" }).fill("OO-2099-9999");
    await page.getByRole("button", { name: "Verify", exact: true }).click();
    await expect(page.getByText("Not on the ledger")).toBeVisible();
  });
});

test.describe("intake", () => {
  test("validation messages and duplicate-evidence feedback", async ({ page }) => {
    await page.goto("/claims/new");
    await page.getByRole("button", { name: "Run checks" }).click();
    await expect(page.getByText("Enter the company making the claim.")).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Claimant" })).toBeFocused();
    await page.getByRole("button", { name: /Clean claim/ }).click();
    await expect(page.getByText(/SHA-256, computed in your browser/)).toBeVisible();
    await expect(page.getByText("Already used as evidence")).toBeVisible(); // seeded Northwind used this file
    await page.locator('input[type="file"]').setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: Buffer.from("x") });
    await expect(page.getByText(/Unsupported type \(\.png\)/)).toBeVisible();
  });
});

test.describe("navigation and layout", () => {
  test("exactly one active app nav item, including on claim detail", async ({ page }) => {
    const nw = await claimId(page, "Northwind");
    await page.goto(`/claims/${nw.id}`);
    const current = page.getByRole("navigation", { name: "Primary" }).locator('[aria-current="page"]');
    await expect(current).toHaveCount(1);
    await expect(current).toHaveText("Claims");
  });

  test("mobile menu opens as a dialog, lists every page and closes with Escape", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.goto("/claims");
    await page.getByRole("button", { name: "Open menu" }).click();
    const menu = page.getByRole("dialog", { name: "Site menu" });
    await expect(menu).toBeVisible();
    for (const label of ["Overview", "Claims", "Cross-Registry", "Observatory", "Assessment", "Verify", "Evidence", "Check a claim"]) {
      await expect(menu.getByRole("link", { name: label, exact: true })).toBeVisible();
    }
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
    await ctx.close();
  });

  test("no horizontal overflow at 320 px on key pages", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 320, height: 640 } });
    const page = await ctx.newPage();
    const helios = await claimId(page, "Helios");
    for (const path of ["/", "/overview", "/claims", "/claims/new", `/claims/${helios.id}`, "/cross-registry", "/observatory", "/assessment", "/verify", "/evidence"]) {
      await page.goto(path);
      const [sw, cw] = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
      expect(sw, `${path} scrollWidth`).toBeLessThanOrEqual(cw);
    }
    await ctx.close();
  });

  test("old /evaluation route redirects and unknown routes have a heading", async ({ page }) => {
    await page.goto("/evaluation");
    await expect(page).toHaveURL(/\/evidence$/);
    await page.goto("/no-such-page");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("This page isn't on the ledger.");
  });
});

test.describe("Stage 4 unified assessment and reconciliation workflows", () => {
  test("assessment console executes evaluation and renders explainable scorecard", async ({ page }) => {
    await page.goto("/assessment");
    await expect(page.getByRole("heading", { name: "Unified Risk Assessment Console" })).toBeVisible();
    // Click demo preset for VCS Project 1904
    await page.getByRole("button", { name: "VCS Project 1904" }).click();
    // Scorecard should render
    await expect(page.getByText("Assessment Target:")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Triggered Rules")).toBeVisible();
    await expect(page.getByText("Evidence Items & Cluster Analysis")).toBeVisible();
  });

  test("rules catalog modal opens, filters, and displays deterministic rule definitions", async ({ page }) => {
    await page.goto("/assessment");
    await page.getByRole("button", { name: "Rules Catalog" }).click();
    const modal = page.getByRole("dialog", { name: "Deterministic Risk Rules Catalog" });
    await expect(modal).toBeVisible();
    await expect(page.getByText("16 Versioned Evaluation Rules")).toBeVisible();
    // Search for a specific rule
    await page.getByPlaceholder(/Search by rule ID/).fill("RULE-INT-001");
    await expect(page.getByText("RULE-INT-001").first()).toBeVisible();
    // Close modal
    await page.getByRole("button", { name: "Close Catalog" }).click();
    await expect(modal).toBeHidden();
  });

  test("claim page tabs switch between Ruler, Assessment, and Allocation Reconciliation", async ({ page }) => {
    const helios = await claimId(page, "Helios");
    await page.goto(`/claims/${helios.id}`);
    await expect(page.getByRole("tab", { name: "Unit Intervals & Ruler" })).toBeVisible();

    // Switch to Unified Risk Assessment tab
    await page.getByRole("tab", { name: /Unified Risk Assessment/ }).click();
    await expect(page.getByRole("heading", { name: "Unified Risk Assessment Scorecard" })).toBeVisible();

    // Switch to Allocation Reconciliation tab
    await page.getByRole("tab", { name: /Allocation Reconciliation/ }).click();
    await expect(page.getByRole("heading", { name: "Allocation-Aware Interval Reconciliation" })).toBeVisible();
    // In Helios claim, interval collision with Equinox is flagged
    await expect(page.getByText("Direct Interval Overlap Conflict")).toBeVisible();
  });
});

test.describe("Sprint 3.3 cross-registry project and entity intelligence workspace", () => {
  test("macro summary census and comparative retirement pacing trends render accurately", async ({ page }) => {
    await page.goto("/cross-registry");
    await expect(page.getByRole("heading", { name: "Cross-Registry Intelligence" })).toBeVisible();

    // Verify macro census metrics
    await expect(page.getByText("Verra VCS Retired Volume")).toBeVisible();
    await expect(page.getByText("Gold Standard Retired Volume")).toBeVisible();
    await expect(page.getByText("Pure Retirement Accounting")).toBeVisible();
    await expect(page.getByText(/669 Excluded/)).toBeVisible();

    // Verify pacing chart
    await expect(page.getByRole("region", { name: "Comparative Retirement Pacing & Volume Trends" })).toBeVisible();
    await expect(page.getByText("Verra VCS Pacing")).toBeVisible();
    await expect(page.getByText("Gold Standard Pacing")).toBeVisible();

    // Toggle data table
    await page.getByRole("button", { name: "Show Table" }).click();
    await expect(page.getByText("Data Table — YEARLY PACING")).toBeVisible();
    await page.getByRole("button", { name: "Hide Table" }).click();
    await expect(page.getByText("Data Table — YEARLY PACING")).toBeHidden();
  });

  test("correlation explorer filters candidates and inspects pairwise comparison modal", async ({ page }) => {
    await page.goto("/cross-registry");
    await expect(page.getByRole("tab", { name: /Correlation Explorer/ })).toBeVisible();

    // Verify candidate pairs are rendered
    await expect(page.getByText("Name Similarity").first()).toBeVisible({ timeout: 10_000 });

    // Open pairwise inspection modal
    await page.getByRole("button", { name: "Inspect Pair" }).first().click();
    const modal = page.getByRole("dialog", { name: "Cross-Registry Project Comparison Detail" });
    await expect(modal).toBeVisible();
    await expect(modal.getByText("Deterministic Lexical Metrics")).toBeVisible();
    await expect(modal.getByText("Attribute Relation Matrix")).toBeVisible();

    // Close modal
    await modal.getByRole("button", { name: "Close Detail" }).click();
    await expect(modal).toBeHidden();
  });

  test("project comparator studio runs presets and flags identifier collisions with safety invariant", async ({ page }) => {
    await page.goto("/cross-registry");
    // Switch to Project Comparator tab
    await page.getByRole("tab", { name: /Project Comparator/ }).click();
    await expect(page.getByText("Quick Demonstration Presets:")).toBeVisible();

    // Click Preset 2: Identifier Collision (VCS 1845 vs GS 1845)
    await page.getByRole("button", { name: /Identifier Collision/ }).click();
    await page.getByRole("button", { name: "Compare Project Profiles" }).click();

    // Verify collision safety banner
    await expect(page.getByText("Cross-Registry Identifier Collision Detected")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/uncoordinated identifier namespaces/)).toBeVisible();

    // Click Preset 1: Attribute Correlation (VCS 1904 vs GS 3044)
    await page.getByRole("button", { name: /Attribute Correlation/ }).click();
    await page.getByRole("button", { name: "Compare Project Profiles" }).click();
    await expect(page.getByText("Partial Attribute Correlation")).toBeVisible({ timeout: 10_000 });
  });

  test("entity & broker studio executes entity resolution and intermediary narrative extraction", async ({ page }) => {
    await page.goto("/cross-registry");
    // Switch to Entity & Broker Studio tab
    await page.getByRole("tab", { name: /Entity & Broker Studio/ }).click();
    await expect(page.getByText("Entity Resolution & Legal Non-Equivalence Mandate")).toBeVisible();

    // Run Entity Resolution
    await page.getByRole("button", { name: "Compare Entity Names" }).click();
    await expect(page.getByText("Resolution Scorecard")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Canonical Variant")).toBeVisible();

    // Run Intermediary Extraction
    await page.getByRole("button", { name: "Extract Intermediary Structure" }).click();
    await expect(page.getByText("Structured Extraction")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Delegated Retirement")).toBeVisible();
    await expect(page.getByText("South Pole Carbon Asset Management Ltd")).toBeVisible();
    await expect(page.getByText("Apple Inc.")).toBeVisible();
  });
});

test.describe("Sprint 3.4 market population & temporal dynamics observatory", () => {
  test("population census overview renders dual-track disclosure and registry distributions", async ({ page }) => {
    await page.goto("/observatory");
    await expect(page.getByRole("heading", { name: "Market Population & Temporal Dynamics Observatory" })).toBeVisible();

    // Verify census tiles
    await expect(page.getByText("Retirement Population Volume")).toBeVisible();
    await expect(page.getByText("Issuance Batches Surveyed")).toBeVisible();
    await expect(page.getByText("Beneficiary Record Disclosure")).toBeVisible();
    await expect(page.getByText("Beneficiary Volume Disclosure")).toBeVisible();

    // Verify registry breakdown
    await expect(page.getByText("Verra (VCS) Registry Population")).toBeVisible();
    await expect(page.getByText("Gold Standard (GS) Registry Population")).toBeVisible();

    // Verify dual-track classification categories
    await expect(page.getByText("Non-Placeholder Disclosed")).toBeVisible();
    await expect(page.getByText("Explicitly Undisclosed")).toBeVisible();
    await expect(page.getByText("Invalid or Placeholder")).toBeVisible();
    await expect(page.getByText(/Methodological Principle/)).toBeVisible();
  });

  test("beneficiary concentration track displays HHI, inequality duality, and interactive Lorenz curve", async ({ page }) => {
    await page.goto("/observatory");
    // Switch to Concentration & Lorenz track
    await page.getByRole("tab", { name: /Concentration & Lorenz/ }).click();

    // Verify HHI and inequality tiles
    await expect(page.getByText("Herfindahl-Hirschman Index (HHI)")).toBeVisible();
    await expect(page.getByText("High Dispersion (HHI < 500)")).toBeVisible();
    await expect(page.getByText("Pooled Allocation Gini (Macro Inequality)")).toBeVisible();
    await expect(page.getByText("Across-Batch Mean Gini (Micro Uniformity)")).toBeVisible();

    // Verify Lorenz curve component
    await expect(page.getByRole("region", { name: "Portfolio Beneficiary Allocation Lorenz Curve" })).toBeVisible();
    await expect(page.getByText(/Gini: 0.9605/)).toBeVisible();

    // Toggle decile table
    await page.getByRole("button", { name: "Decile Table" }).click();
    await expect(page.getByText(/Empirical Decile Distribution Breakdown/)).toBeVisible();
    await page.getByRole("button", { name: "Hide Deciles" }).click();
    await expect(page.getByText(/Empirical Decile Distribution Breakdown/)).toBeHidden();

    // Verify top disclosed beneficiaries ranking table
    await expect(page.getByText("Top Disclosed Beneficiaries by Claimed Volume")).toBeVisible();
    await expect(page.getByText("Telstra Corporation Limited")).toBeVisible();
    await expect(page.getByText("Shell")).toBeVisible();
  });

  test("batch fragmentation explorer inspects batches, micro-claims, and interval topologies", async ({ page }) => {
    await page.goto("/observatory");
    // Switch to Batch Fragmentation track
    await page.getByRole("tab", { name: /Batch Fragmentation/ }).click();
    await expect(page.getByText("Batch Fragmentation & Interval Structure Inspector")).toBeVisible();

    // Inspect default/first preset (VCS 10918)
    await expect(page.getByText("Within-Batch Gini Coefficient")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Absolute Micro-Claims/)).toBeVisible();
    await expect(page.getByText(/Relative Small Tranches/)).toBeVisible();

    // Verify interval topology
    await expect(page.getByText("Batch Interval Topology & Integrity Check")).toBeVisible();
    await expect(page.getByText("0 Overlaps")).toBeVisible();

    // Click Istanbul Landfill preset (GS GS1-1-TR-GS707-21-2016-20993)
    await page.getByRole("button", { name: /Istanbul Landfill/ }).click();
    await expect(page.getByText("LANDFILL GAS EXTRACTION")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("432,388 t")).toBeVisible();
  });

  test("temporal dynamics track toggles monthly, weekly, and daily timelines, bursts, and gaps", async ({ page }) => {
    await page.goto("/observatory");
    // Switch to Temporal Dynamics track
    await page.getByRole("tab", { name: /Temporal Dynamics/ }).click();

    // Verify Temporal Activity Chart
    await expect(page.getByRole("region", { name: "Temporal Activity & Velocity Trends" })).toBeVisible();
    await expect(page.getByText("Observed Window Volume")).toBeVisible();

    // Toggle to weekly
    await page.getByRole("button", { name: "weekly" }).click();
    await expect(page.getByRole("button", { name: "weekly" })).toHaveAttribute("aria-pressed", "true");

    // Toggle to daily
    await page.getByRole("button", { name: "daily" }).click();
    await expect(page.getByRole("button", { name: "daily" })).toHaveAttribute("aria-pressed", "true");

    // Toggle back to monthly
    await page.getByRole("button", { name: "monthly" }).click();

    // Verify MAD-based bursts inspector
    await expect(page.getByText("MAD-Based Liquidation Bursts")).toBeVisible();
    await expect(page.getByText(/Anomaly Periods Detected/)).toBeVisible();

    // Verify Zero-Activity Gaps Inspector
    await expect(page.getByText("Reporting Inactivity Intervals")).toBeVisible();
    await expect(page.getByText(/Gaps \(Mean:/)).toBeVisible();
  });
});
