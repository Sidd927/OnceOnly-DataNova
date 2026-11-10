# OnceOnly: Final Demo Runbook (DATANOVA 2026)

This runbook takes a clean machine to a running demo, validates it, and lists fallbacks. The narration and click path are in [`FINAL_DEMO_SCRIPT.md`](FINAL_DEMO_SCRIPT.md).

## 0. Requirements

- Python 3.12 and Node 20+ (tested with Node 26.4), plus `make`.
- Docker, for option A: Docker Desktop or Colima.
- Nothing secret is needed. `.env` is created from `.env.example` and contains only the **publicly known Hardhat development keys**, which work on the local chain only. The backend refuses to use them on any other chain.

## A. One container (recommended for judges)

```bash
git clone https://github.com/Sidd927/OnceOnly-DataNova.git
cd OnceOnly-DataNova
git checkout datanova/phase-0-baseline   # until the owner merges it into main
make docker-build                        # about 2–5 min cold
make docker-run                          # serves http://127.0.0.1:7860
```

At boot the container:

1. starts a private Hardhat chain on its loopback;
2. deploys `ClaimLedger`;
3. seeds the five-claim story through a private write-enabled API;
4. prints `fingerprint c544f5897354081cf1d20efb366b951f14d2b8ffa69bcb87b105cfdc0df6483b`;
5. serves the API and UI in **public-demo mode**: ledger writes return 403 and claim checks are rate-limited.

Measured on 2026-11-10 (Colima):

| Measure | Result |
|---|---|
| Idle memory | 277 MiB |
| Peak memory under concurrent analytics | 290 MiB |
| Analytics response time | 0.04–0.8 s |

## B. Development stack (four terminals)

```bash
make setup                        # once
make chain                        # 1: Hardhat on 127.0.0.1:8545
make deploy && make api           # 2: contract, then API on 127.0.0.1:8000
make web                          # 3: UI on http://127.0.0.1:5173
make seed && make demo-check      # 4: seed the story; print the fingerprint
```

If port 8000 is busy, run the API on another port and pass `ONCEONLY_API`:

```bash
cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
ONCEONLY_API=http://127.0.0.1:8010 make web
ONCEONLY_API=http://127.0.0.1:8010 make seed
ONCEONLY_API=http://127.0.0.1:8010 make demo-check
```

To serve the built UI from the API (as the container does), build it with `cd frontend && npm run build` and start the API with `ONCEONLY_STATIC_DIR=frontend/dist`.

**Reset to the exact story:** run `make reset` (deletes `var/onceonly.sqlite` and `var/evidence/`, then deploys a fresh contract), restart the API, then `make seed && make demo-check`.

## C. Validate before presenting

| Check | Command | Expected |
|---|---|---|
| Health | `curl -s <base>/api/health` | `chain.available: true`, `reference.scope: demo-subset`, `analytics.available: true` |
| Fingerprint | `make demo-check` | `c544f589…6483b` |
| Browser suite | `cd frontend && BASE_URL=<base> npx playwright test` | 45 passed on the dev stack |
| Population figures | `curl -s <base>/api/analytics/population/summary` | 37,335 records; `hhi_disclosed` 245.64 |
| Verification | Open `/verify?ref=OO-2026-0001` and click **Original document** | 6 of 7 checks pass (claimant check not performed); document `ONCHAIN_ROOT_MATCH` |

`make e2e` needs a **fresh, unseeded** ledger: `make reset`, restart the API, `make e2e`, then reset and seed again for the demo.

## D. Demo navigation (seeded story)

| Claim | Story | Expected state |
|---|---|---|
| OO-2026-0001 Northwind | Clean claim | Anchored (ledger claim #1) |
| OO-2026-0002 Helios | Overlaps Northwind by 4,559 units | Blocked, with one contract rejection (`RangeOverlap`) |
| OO-2026-0003 Arbor | Gold Standard and Verra blocks | Anchored (ledger claim #2) |
| OO-2026-0004 Lumen | Mistyped batch (18435) | Checked, needs review (not found in snapshot) |
| OO-2026-0005 Kestrel | No serials | Blocked (`EVD-001`) |

Path: `/` → `/overview` → `/claims/2` (Ruler, then Allocation Reconciliation) → `/assessment` (Helios · claim 2) → `/cross-registry` (Project Comparator, Identifier Collision) → `/observatory` (Concentration & Lorenz) → `/verify?ref=OO-2026-0001` (Original document, then Tampered copy) → `/evidence`.

## E. Fallbacks

| Problem | Fallback |
|---|---|
| Docker unavailable | Use option B |
| Port 8000 taken | Use another port with `ONCEONLY_API`, as in B |
| Chain restarted, so the API reports "No contract code" | `make deploy`, restart the API, `make seed` (or `make reset` first) |
| Fingerprint differs | `make reset`, restart the API, `make seed`. A different fingerprint means state differs from the canonical story; report it, don't hide it |
| Live demo impossible | Play `docs/submission/OnceOnly_DATANOVA_Demo_720p.mp4` (recorded from the real app) and show the screenshots in `docs/assets/datanova/` |
| Analytics endpoints return 503 `ANALYTICS_DB_UNAVAILABLE` | Ensure `data/reference/demo_subset.csv.gz` exists. The database is materialized at `ONCEONLY_REFERENCE_DEMO_DB` (default `var/registry_demo.sqlite`) |

## F. Public demo URL (owner action)

No public instance exists yet: deploying needs the owner's hosting account, and none is configured on the build machine. The image is ready, and [`render.yaml`](../../render.yaml) is a prepared blueprint (Docker runtime, free plan, `/api/health`, public-demo mode, `autoDeploy: false`). The image fits the free tier's 512 MB at about 290 MiB peak.

1. Sign in at https://dashboard.render.com with GitHub. The repository is already public.
2. Choose **New → Blueprint**, select `Sidd927/OnceOnly-DataNova`, and choose branch **`datanova/phase-0-baseline`**. `main` does not contain the DATANOVA work.
3. Apply. The first build takes several minutes, and the boot seeds the demo.
4. Smoke test:
   ```bash
   curl -s https://<service>.onrender.com/api/health
   ```
   It should show `"public_demo":true` and `"analytics":{"available":true,...}`. Then open `/claims/2` and `/verify?ref=OO-2026-0001`.
5. Optionally run the browser suite: `cd frontend && BASE_URL=https://<service>.onrender.com npx playwright test`. Tests that submit or anchor claims are expected to be refused (403) or rate-limited in public-demo mode.
6. Paste the URL into the submission form with this label: *"Demo instance: ledger writes disabled; the contract runs on a private local chain inside the container; may take about a minute to wake."*

Detailed environment variables, security notes and rollback steps are in [`08_deployment_runbook.md`](08_deployment_runbook.md), section C. The repository name there is current; use the branch above instead of `main`.

## G. Re-recording the demo video

With the seeded stack running:

```bash
cd frontend
BASE_URL=http://127.0.0.1:8010 BEATS=./beats_datanova.mjs DEMO_NAME=demo_datanova node qa/demo/record.mjs
```

This needs ffmpeg and macOS `say`. Output goes to `exports/demo_datanova/` (gitignored). The committed 720p copy was produced with:

```bash
ffmpeg -i demo_datanova.mp4 -vf scale=1280:720 -c:v libx264 -crf 26 -c:a aac -b:a 96k -movflags +faststart \
  docs/submission/OnceOnly_DATANOVA_Demo_720p.mp4
```
