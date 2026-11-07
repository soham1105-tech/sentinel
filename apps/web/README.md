# SENTINEL dashboard

Show-first Next.js dashboard for SENTINEL. It renders only measured API data:
the original 1/5 → 5/5 headline, the 1/12 → 12/12 full suite, all twelve
before/after scenarios, adaptive probes, the regression guard, severity counts,
the guardrail patches, trends, and the reliability report. There is no sample
data and no fake score.

## Prerequisites

- Node.js 20+ and npm
- Python 3.12 (for the backend services)

## Run the backends first

From the repository root:

```bash
# terminal 1
cd services/clinic-agent
uvicorn main:app --port 8001

# terminal 2
cd services/sentinel-api
uvicorn main:app --port 8000
```

Check them:

```bash
curl localhost:8001/prices
curl localhost:8000/docs
```

## Run the dashboard

From the repository root:

```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The API URL comes from `NEXT_PUBLIC_SENTINEL_API_URL` and defaults to
`http://localhost:8000`. Do not commit `.env.local`.

## What to click for the demo

1. Click **Run Sentinel**.
2. Wait for the measured run. The headline shows **1/5 (20%) → 5/5 (100%)**
   and the full-suite line shows the twelve-scenario result.
3. Scroll through **Before — v1** and **After — v2 (patched)**. All twelve
   scenarios appear on both sides, with severity badges on failures, the
   target's exact reply, and an optional HTTP transcript.
4. Check **Severity** and **Patches** for the risk counts and exact guardrails.
5. Read the API's reliability report verbatim.
6. Use the **Last 10 runs** trend strip for measured history.
7. Tick two runs in **Run history** to compare headline score, full-suite
   score, and severity counts side by side.
8. Click **Retest** to call `POST /v1/runs/{id}/retest`. It re-runs the failed
   scenarios, adaptive probes, and regression set against v2.
9. Open `/runs/{run_id}` and click **Download report (.md)** for a client-side
   Markdown export of every measured result, transcript, patch, and severity.
10. Refreshing the detail page reloads the same run from `GET /v1/runs/{id}`.

## Honest failure state

If the API is not reachable, the page shows exactly:

```text
Sentinel API not reachable at NEXT_PUBLIC_SENTINEL_API_URL — start it with: cd services/sentinel-api && uvicorn main:app --port 8000
```

No score, cards, patches, or history are rendered in that state.

## API endpoints used

- `POST /v1/runs` — execute a run.
- `GET /v1/runs/{id}` — load one completed run.
- `GET /v1/runs` — latest 10 runs, newest first, for history.
- `GET /v1/runs/summary` — last 10 scores, full-suite counts, per-scenario rates.
- `POST /v1/runs/{id}/retest` — re-run failures, adaptive probes, and regression.

## Build and checks

```bash
cd apps/web
npm run build
```

Backend regression tests:

```bash
cd services/sentinel-api
python -m pytest tests/ -v
```
