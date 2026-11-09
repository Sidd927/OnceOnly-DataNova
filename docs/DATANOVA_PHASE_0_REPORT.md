# ONCEONLY — DATANOVA 2026 PHASE 0 REPORT
## Engineering Baseline, Environment Setup & Repository Hygiene

**Date:** November 8, 2026  
**Author / Roles:** Principal Software Architect, Full-Stack Engineering Lead, QA Director  
**Repository:** `OnceOnly-DataNova`  
**Active Working Branch:** `datanova/phase-0-baseline`  
**Git Remote:** `origin` -> `https://github.com/Sidd927/OnceOnly-DataNova.git`  
**Status:** Phase 0 Implementation Complete & Verified  

---

## 1. Initial Repository State
- **Initial Branch:** `main` (clean working tree tracking `origin/main`).
- **Initial Commit:** `6a61655 docs: elevate OnceOnly README and project visuals`.
- **Pre-existing State:** The repository contained the complete codebase (contracts, backend, frontend, demo data, test scripts) from the prior engineering cycle. The four comprehensive technical audit documents (`docs/DATANOVA_BASELINE_AUDIT.md`, `docs/DATANOVA_DATA_ASSESSMENT.md`, `docs/DATANOVA_TEST_RESULTS.md`, `docs/DATANOVA_UPGRADE_ROADMAP.md`) were generated and present in the untracked working tree.
- **Environment State:** Neither `.venv` nor `node_modules` (in contracts/frontend) existed in the cloned workspace.

---

## 2. Git Branch & Remote Verification
- **Working Branch:** Created and checked out isolated development branch:
  ```bash
  git checkout -b datanova/phase-0-baseline
  ```
- **Remote Verification:**
  - `origin (fetch)`: `https://github.com/Sidd927/OnceOnly-DataNova.git`
  - `origin (push)`: `https://github.com/Sidd927/OnceOnly-DataNova.git`
- **Isolation Confirmation:**
  - The legacy `ClimateChain` repository is **not** configured as a remote, upstream, or push destination.
  - History is intact (26 commits). No commits have been rewritten or deleted.
  - **No commits or pushes were made** during this phase, honoring the non-committal mandate.

---

## 3. Environment Requirements & Runtime Specifications
- **Operating System:** macOS Darwin (Apple Silicon arm64) / Linux x86_64 compatible.
- **Python Runtime:** Python 3.12 (specifically `/opt/homebrew/bin/python3.12` v3.12.13).
- **Node.js Runtime:** Node.js v26.4.0 (Node 22 LTS or higher compatible).
- **Package Manager:** npm v11.17.0.
- **Solidity Compiler:** Solc 0.8.24 (EVM target: Paris, optimizer enabled: 200 runs).

---

## 4. Python Backend Setup
- **Virtual Environment:** Project-local virtual environment created under `.venv` using Python 3.12:
  ```bash
  python3.12 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r backend/requirements.txt
  ```
- **Dependencies Installed:** 
  `fastapi==0.115.14`, `uvicorn[standard]==0.32.1`, `web3==7.16.0`, `eth-utils==6.0.0`, `pydantic==2.14.3`, `pypdf==5.9.0`, `rapidfuzz==3.14.6`, `reportlab==4.5.1`, `openpyxl==3.1.5`, `pandas==2.3.3`, `pytest==8.4.2`, `httpx==0.27.2`, and `anthropic==2.6.0`.
- **Zero Global Pollution:** All packages isolated to `.venv/` (gitignored).

---

## 5. Frontend Setup
- **Dependencies Installed:** Installed cleanly via existing lockfile in `frontend/`:
  ```bash
  cd frontend && npm install --no-fund --no-audit
  ```
- **Build Verification:**
  ```bash
  cd frontend && npm run build
  ```
  *Result:* TypeScript (`tsc -b`) and Vite production bundle generated cleanly (`dist/` 327.57 kB JS, 53.65 kB CSS) with **0 errors in 231ms**.
- **Linting Verification:**
  ```bash
  cd frontend && npm run lint
  ```
  *Result:* `oxlint` reported **0 warnings and 0 errors** across 31 files.

---

## 6. Smart-Contract Setup
- **Dependencies Installed:** Installed cleanly via existing lockfile in `contracts/`:
  ```bash
  cd contracts && npm install --no-fund --no-audit
  ```
- **Compilation:**
  ```bash
  cd contracts && npx hardhat compile
  ```
  *Result:* `Compiled 2 Solidity files successfully (evm target: paris).` (`ClaimLedger.sol` and `ClaimLedgerLinear.sol`).
- **Telemetry Prompt Silencing:** Added `HARDHAT_DISABLE_TELEMETRY_PROMPT=true` to `Makefile` targets to ensure non-interactive execution.

---

## 7. Exact Local Startup Commands

The application stack can be launched via standard Make targets:

1. **Terminal 1 — Local Hardhat Blockchain (port 8545):**
   ```bash
   make chain
   # or: cd contracts && npx hardhat node --hostname 127.0.0.1 --port 8545
   ```
2. **Terminal 2 — Deploy ClaimLedger Smart Contract:**
   ```bash
   make deploy
   # or: cd contracts && npx hardhat run scripts/deploy.js --network localhost
   ```
3. **Terminal 3 — FastAPI Backend Service (port 8000):**
   ```bash
   make api
   # or: cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
4. **Terminal 4 — Vite Frontend UI (port 5173):**
   ```bash
   make web
   # or: cd frontend && npm run dev -- --host 127.0.0.1
   ```
5. **Seeding the Demo Workflow:**
   ```bash
   make seed
   # or: .venv/bin/python backend/scripts/seed_demo.py
   ```
6. **Verifying State Fingerprint:**
   ```bash
   make demo-check
   # or: .venv/bin/python backend/scripts/demo_fingerprint.py
   ```

---

## 8. Exact Testing Commands

- **Run All Tests (Contracts + Backend):**
  ```bash
  make test
  ```
- **Backend Tests Only:**
  ```bash
  make test-backend
  # or: cd backend && ../.venv/bin/python -m pytest -q -p no:warnings
  ```
- **Contract Tests & Gas Benchmark:**
  ```bash
  make test-contracts
  # or: cd contracts && HARDHAT_DISABLE_TELEMETRY_PROMPT=true npx hardhat test
  ```
- **End-to-End API & Chain Smoke Test (Requires running chain & API):**
  ```bash
  .venv/bin/python eval/e2e_smoke.py
  ```
- **Frontend Code Quality:**
  ```bash
  cd frontend && npm run lint
  cd frontend && npm run build
  ```

---

## 9. Baseline Test Results

```
========================================================================================================
TEST SUITE                 COMMAND                                    OUTCOME               DURATION
========================================================================================================
Contract Unit & Invariants cd contracts && npx hardhat test          24 passed, 0 failed   1.0s
Backend Serial Parser      .venv/bin/pytest backend/tests/test_serials 8 passed, 0 failed    0.12s
Backend Service & Rules    .venv/bin/pytest backend/tests/test_service 16 passed, 0 failed   3.23s
Full Backend Suite         make test-backend                          24 passed, 0 failed   3.35s
Frontend TypeScript Build  cd frontend && npm run build               0 errors, 0 warnings  0.23s
Frontend Linter            cd frontend && npm run lint                0 errors, 0 warnings  0.03s
End-to-End Smoke Test      .venv/bin/python eval/e2e_smoke.py         13/13 checks passed   1.2s
Demo State Determinism     make demo-check                            Fingerprint verified  0.4s
========================================================================================================
```

### Empirical Validation Findings
1. **Gas Invariant:** Hinted $O(1)$ linked list measured flat at **301,452 gas** across 10, 50, and 200 existing ranges; linear scan scaled from 314,288 to **832,608 gas**.
2. **Double-Use Revert:** In `eval/e2e_smoke.py`, Helios Apparel's forced registration reverted on-chain with exact custom error:
   `RangeOverlap(bytes32 ns, uint256 existingClaimId=1, uint64 overlapStart=896315001, uint64 overlapEnd=896319559)`.
3. **Deterministic State Fingerprint:** `make reset` -> restart API -> `make seed` -> `make demo-check` output:
   `fingerprint c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`
   This is **100% bit-exact** with the historical benchmark recorded in project records.

---

## 10. Issues Discovered

1. **Environment Omission in Cloned State:** The repository clone did not have `.venv` pre-initialized, causing system Python (`/usr/bin/python3`) to fail with `ModuleNotFoundError: No module named 'eth_utils'`.
2. **Hardhat Interactive Telemetry Prompt:** Running `npx hardhat test` hung waiting for an interactive VS Code prompt when `HARDHAT_DISABLE_TELEMETRY_PROMPT` was not exported.
3. **Stale Repository URLs:** Active documentation and runbooks cited `https://github.com/Sidd927/ClimateChain`.
4. **Hackathon Badges in README:** `README.md` displayed an `IEEE_ClimateChain_2026` track badge and hackathon footer attribution.

---

## 11. Issues Resolved

1. **Virtual Environment Established:** Created `.venv` using Python 3.12 and installed all dependencies from `backend/requirements.txt`.
2. **Makefile Hardhat Automation:** Updated `Makefile` lines 64 and 67 to set `HARDHAT_DISABLE_TELEMETRY_PROMPT=true`, eliminating interactive hangs in automated test runs.
3. **Repository URLs Updated:** Updated stale URLs in `docs/submission/` (6 files) to point to `https://github.com/Sidd927/OnceOnly-DataNova`.
4. **README Brand Neutralization:** Replaced IEEE hackathon badge with domain-specific `"Carbon Markets & Emissions Transparency"` badge; updated directory layout to `OnceOnly/`; updated footer attribution to reflect continuous research and development.
5. **Environment Configuration File:** Ensured `.env` exists from `.env.example` without overwriting custom settings.

---

## 12. Remaining Issues & Deferrals (Phase 1+ Scope)

1. **Full Dataset Benchmark Fallback (Phase 1):** `eval/run_eval.py` requires `registry_full.sqlite` and currently crashes if the full 67 MB download has not been executed. It must be refactored to fall back gracefully to `demo_subset.csv.gz`.
2. **Table & OCR Parsing Limitations (Phase 1):** Serial extraction recall on table columns and prose ranges remains 0% until tabular parsing and digit healing are implemented in Phase 1.
3. **Mojibake in Project Names (Phase 1):** Source dataset strings containing UTF-8 double-encoding artifacts (e.g., `'Guanaré'`) require an automated normalization pass during ingestion.

---

## 13. Branding Cleanup Performed & Retained

### Modified for Identity Clarity:
- `README.md:13`: Replaced `IEEE_ClimateChain_2026` badge with domain badge `Carbon_Markets_&_Emissions_Transparency`.
- `README.md:317`: Changed `ClimateChain/` to `OnceOnly/` in project layout diagram.
- `README.md:379`: Neutralized footer attribution from hackathon-specific text to independent creator attribution.
- `docs/submission/00_current_state_audit.md`: Updated directory path and remote URL to `OnceOnly-DataNova`.
- `docs/submission/01_devpost_submission.md:105`: Updated source code link to `https://github.com/Sidd927/OnceOnly-DataNova`.
- `docs/submission/05_submission_compliance_checklist.md:19`: Updated repository URL.
- `docs/submission/06_final_submission_runbook.md:6, 114`: Updated clone URLs.
- `docs/submission/08_deployment_runbook.md:87`: Updated Render repo selector.
- `docs/submission/09_demo_recording_checklist.md:37`: Cleaned video title.

### Intentionally Retained:
- `data/LICENSE`: Retained full CC BY 4.0 Berkeley attribution and rights limitation disclosures.
- `docs/01_hackathon_requirements.md` & `docs/04_research_sources.md`: Retained as genuine historical records of prior research.

---

## 14. Security & Configuration Hygiene Findings
- **Secret Scanning:** No exposed API keys, bearer tokens, or funded private keys were discovered in working files or Git history.
- **Development Key Isolation:** Publicly known Hardhat keys (#0 and #2) in `.env.example` and `Dockerfile` are strictly flagged and verified to operate exclusively when `chainId == 31337`.
- **Runtime File Exclusions:** Verified that `.env`, `var/`, `data/raw/`, `contracts/artifacts/`, and `dist/` are safely ignored by `.gitignore`.

---

## 15. Reproducibility Status
**100% REPRODUCIBLE.**  
From a clean environment with Python 3.12 and Node 22:
- `make setup` configures virtualenv, installs all node packages, and compiles contracts.
- `make test` runs 48 passing tests (24 contract + 24 backend) in under 5 seconds.
- `make reset` + `make seed` + `make demo-check` produces the exact bit-level fingerprint `c544f589…6483b`.

---

## 16. Phase 1 Readiness Assessment
**Phase 0 is successfully completed.**  
The repository is isolated on `datanova/phase-0-baseline`, dependencies are pinned and verified, tests pass 100%, and brand identity is aligned with OnceOnly.

The project is fully prepared to enter **PHASE 1: DATA FOUNDATION & RESILIENT INGESTION**.

