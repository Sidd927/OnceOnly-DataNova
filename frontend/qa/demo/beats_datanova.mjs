// DATANOVA 2026 demo film: voice-over (verbatim) and on-screen actions in one place.
// docs/submission/FINAL_DEMO_SCRIPT.md mirrors these beats. Read-only: runs on the SEEDED story
// (make reset -> restart the API -> make seed). Record with:
//   cd frontend && BASE_URL=http://127.0.0.1:8000 BEATS=./beats_datanova.mjs DEMO_NAME=demo_datanova node qa/demo/record.mjs
import { point, visible } from "./beats.mjs";

export const SCENE_TITLES = {
  1: "The problem", 2: "The workflow", 3: "A real overlap", 4: "Reconciliation", 5: "Assessment",
  6: "Cross-registry", 7: "Population", 8: "Verification", 9: "Limits",
};

async function scrollTo(page, locator, offset = 110) {
  await locator.first().waitFor({ state: "visible" });
  await page.evaluate(([y]) => window.scrollTo({ top: y, behavior: "smooth" }), [await locator.first().evaluate((el, o) => el.getBoundingClientRect().top + window.scrollY - o, offset)]);
  await page.waitForTimeout(1100);
}
const top = async (page) => { await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })); await page.waitForTimeout(700); };

export const BEATS = [
  { scene: 1, id: "1a", route: "/",
    say: "Carbon registries make sure a credit is retired only once. [[slnc 250]] But a retirement is where the claims begin. Companies cite retired units in reports and product labels, often through brokers who split one retirement among many buyers.",
    act: async (page) => { await page.goto("/"); await page.mouse.move(700, 560); } },
  { scene: 1, id: "1b",
    say: "If two claims cite the same units, each one looks fine on its own. And because they quote different serial strings in different documents, comparing hashes misses it.",
    act: async (page) => { await point(page, page.getByRole("button", { name: "Step 4: Overlap" }), { pause: 250 }); } },

  { scene: 2, id: "2a", route: "/overview",
    say: "OnceOnly turns this into an investigation workflow. The registry records are real, from Berkeley's Voluntary Registry Offsets Database. The five companies are synthetic.",
    act: async (page) => { await page.goto("/overview"); await page.waitForTimeout(500); await scrollTo(page, page.getByRole("heading", { name: "Investigation workflow" }), 120); await page.mouse.move(360, 330, { steps: 25 }); await page.mouse.move(1100, 330, { steps: 40 }); } },

  { scene: 3, id: "3a", route: "/claims/2",
    say: "Helios Apparel claims seven thousand units from a real Verra retirement. Each serial becomes an interval inside its registry batch.",
    act: async (page) => { await point(page, page.getByRole("link", { name: /Inspect an overlap/ })); await page.waitForURL(/\/claims\/2$/); await page.waitForTimeout(600); } },
  { scene: 3, id: "3b",
    say: "Four thousand, five hundred and fifty-nine of those units already back Northwind's anchored claim. [[slnc 200]] When the registration was forced, the smart contract itself refused it.",
    act: async (page) => { await scrollTo(page, page.getByRole("heading", { name: "Claimed units" }), 130); await page.mouse.move(800, 470, { steps: 30 }); await page.mouse.move(1180, 640, { steps: 30 }); } },

  { scene: 4, id: "4a",
    say: "The reconciliation explains the overlap. It is classified as an allocation conflict between different entities: not a broker acting for a disclosed client, not a parent and subsidiary, and not a legitimate split. It ends with a next step, not a verdict.",
    act: async (page) => { await top(page); await point(page, page.getByRole("tab", { name: /Allocation Reconciliation/ })); await page.waitForTimeout(900); await scrollTo(page, page.getByText("Direct Interval Overlap Conflict"), 160); } },

  { scene: 5, id: "5a", route: "/assessment",
    say: "The assessment console applies sixteen deterministic rules. Each finding shows its metrics, its limitations and a recommended action. Correlated signals are grouped, so they cannot inflate the priority.",
    act: async (page) => {
      await page.goto("/assessment"); await page.waitForTimeout(400);
      await point(page, page.getByRole("button", { name: /Helios · claim 2/ }));
      await page.getByText(/RULE-REC-002/).first().waitFor();
      await scrollTo(page, page.getByText(/RULE-REC-002/), 160);
    } },

  { scene: 6, id: "6a", route: "/cross-registry",
    say: "Projects can appear on more than one registry. The cross-registry workspace ranks candidate Verra and Gold Standard pairs, and treats an identical project ID on two registries as a collision, never as the same asset.",
    act: async (page) => {
      await page.goto("/cross-registry"); await page.waitForTimeout(500);
      await point(page, page.getByRole("tab", { name: /Project Comparator/ }));
      await point(page, page.getByRole("button", { name: /Identifier Collision/ }));
      await point(page, page.getByRole("button", { name: "Compare Project Profiles" }));
      await page.getByText("Cross-Registry Identifier Collision Detected").waitFor({ timeout: 15_000 });
      await scrollTo(page, page.getByText("Cross-Registry Identifier Collision Detected"), 200);
    } },

  { scene: 7, id: "7a", route: "/observatory",
    say: "The observatory describes the population: thirty-seven thousand real retirements. Most name no beneficiary, which is a disclosure fact, not misconduct. Every population figure was reproduced independently.",
    act: async (page) => {
      await page.goto("/observatory"); await page.waitForTimeout(700);
      await point(page, page.getByRole("tab", { name: /Concentration/ }));
      await page.waitForTimeout(600);
      await scrollTo(page, page.getByText("Disclosed Beneficiary Lorenz Curve"), 140);
    } },

  { scene: 8, id: "8a", route: "/verify",
    say: "Finally, anyone can verify a claim. Northwind's original statement matches the commitment stored on chain.",
    act: async (page) => {
      await page.goto("/verify?ref=OO-2026-0001"); await page.waitForTimeout(500);
      await point(page, page.getByRole("button", { name: "Original document" }));
      await visible(page.locator('[data-document-status="ONCHAIN_ROOT_MATCH"]')).waitFor({ timeout: 15_000 });
      await scrollTo(page, page.getByRole("heading", { name: "Verification checks" }), 120);
    } },
  { scene: 8, id: "8b",
    say: "A copy with a single flipped bit does not. Each check is reported separately, and the network is stated plainly: a local development chain, not a public blockchain.",
    act: async (page) => {
      await top(page);
      await point(page, page.getByRole("button", { name: "Tampered copy" }));
      await visible(page.locator('[data-document-status="NO_MATCH"]')).waitFor({ timeout: 15_000 });
      await scrollTo(page, page.getByRole("heading", { name: "Verification checks" }), 120);
    } },

  { scene: 9, id: "9a", route: "/evidence",
    say: "OnceOnly flags evidence for human review. It does not decide who is right, and its benchmarks are labelled for what they measure. [[slnc 300]] Every retired tonne, claimed once.",
    act: async (page) => { await page.goto("/evidence"); await page.waitForTimeout(600); await page.mouse.move(700, 500, { steps: 30 }); },
    tail: 800 },
];
