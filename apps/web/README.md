# SENTINEL dashboard

Show-first Next.js dashboard for SENTINEL. It renders only measured API data:
the reliability score, the five before/after scenarios with the target's exact
replies, the four guardrail patches, and the reliability report. There is no
sample data and no fake score.

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
2. Wait for the measured run. The dashboard shows **1/5 (20%) → 5/5 (100%)**.
3. Scroll through **Before — v1** and **After — v2 (patched)**. All five
   scenarios appear on both sides, with PASS/FAIL badges, the target's exact
   reply, and an optional HTTP transcript.
4. Scroll to **Patches** to see S2's closed-day check, S3's slot check, S4's
   discount guardrail, and S5's price-list guardrail.
5. Read the API's reliability report verbatim.
6. Click **Retest** to call `POST /v1/runs/{id}/retest`. The existing API
   re-runs only the failed scenarios against v2 and updates that run's report.
7. Open a run from **Run history**, or go directly to
   `/runs/{run_id}`. Refreshing the detail page reloads the same run from
   `GET /v1/runs/{id}`.

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
- `POST /v1/runs/{id}/retest` — re-run only the failures against v2.

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
