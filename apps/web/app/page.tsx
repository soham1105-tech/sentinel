"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiDown } from "@/components/api-down";
import { RunHistory } from "@/components/run-history";
import { RunView } from "@/components/run-view";
import { SiteHeader } from "@/components/site-header";
import {
  createRun,
  fetchRuns,
  getRememberedRunIds,
  isApiUnreachable,
  pollRun,
  rememberRunId,
  retestRun,
  SentinelApiError,
  type RunReport,
  type RunSummary,
} from "@/lib/api";

function historyEndpointUnavailable(error: unknown): boolean {
  return (
    error instanceof SentinelApiError &&
    (error.kind === "not_found" || error.kind === "unavailable" || error.kind === "http")
  );
}

export default function HomePage() {
  const [run, setRun] = useState<RunReport | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [fallbackRunIds, setFallbackRunIds] = useState<string[]>([]);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [retesting, setRetesting] = useState(false);
  const [apiDown, setApiDown] = useState(false);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const latest = await fetchRuns();
      setRuns(latest);
      setHistoryUnavailable(false);
    } catch (error) {
      if (historyEndpointUnavailable(error)) {
        setFallbackRunIds(getRememberedRunIds());
        setHistoryUnavailable(true);
      } else {
        setApiDown(true);
        setRun(null);
      }
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function load() {
      setHistoryLoading(true);
      try {
        const latest = await fetchRuns();
        if (!active) {
          return;
        }
        setRuns(latest);
        setHistoryUnavailable(false);
      } catch (error) {
        if (!active) {
          return;
        }
        if (historyEndpointUnavailable(error)) {
          setFallbackRunIds(getRememberedRunIds());
          setHistoryUnavailable(true);
        } else {
          setApiDown(true);
        }
      } finally {
        if (active) {
          setHistoryLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  async function handleRun() {
    if (running) {
      return;
    }
    setRunning(true);
    setApiDown(false);
    setStatusNote(null);
    setRun(null);

    try {
      const created = await createRun();
      rememberRunId(created.run_id);
      const completed = await pollRun(created.run_id, created);
      setRun(completed);
      await refreshHistory();
    } catch (error) {
      if (isApiUnreachable(error)) {
        setApiDown(true);
        setRun(null);
      } else {
        setStatusNote(
          error instanceof Error ? error.message : "Sentinel could not complete the run.",
        );
      }
    } finally {
      setRunning(false);
    }
  }

  async function handleRetest() {
    if (!run || retesting) {
      return;
    }
    setRetesting(true);
    setStatusNote(null);

    try {
      const updated = await retestRun(run.run_id);
      rememberRunId(updated.run_id);
      setRun(updated);
      setStatusNote("Retest complete — only the failed scenarios were re-run against v2.");
      await refreshHistory();
    } catch (error) {
      if (isApiUnreachable(error)) {
        setApiDown(true);
        setRun(null);
      } else {
        setStatusNote(
          error instanceof Error ? error.message : "Sentinel could not retest this run.",
        );
      }
    } finally {
      setRetesting(false);
    }
  }

  return (
    <main className="relative isolate mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 sm:py-12">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px] bg-[radial-gradient(ellipse_at_top,rgba(110,231,183,0.07),transparent_62%)]"
      />
      <SiteHeader />

      {apiDown ? (
        <div className="mt-10">
          <ApiDown />
        </div>
      ) : (
        <>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              data-testid="run-sentinel"
              onClick={handleRun}
              disabled={running || retesting}
              className="inline-flex w-fit items-center justify-center rounded-full bg-white px-7 py-3.5 text-sm font-black tracking-wide text-ink shadow-[0_8px_30px_rgba(255,255,255,0.09)] transition hover:-translate-y-0.5 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Run Sentinel
            </button>

            {running ? (
              <div
                role="status"
                data-testid="running"
                className="flex items-center gap-3 text-sm font-semibold text-muted"
              >
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
                Running Sentinel…
              </div>
            ) : (
              <p className="text-xs uppercase tracking-[0.18em] text-muted/70">
                Live HTTP evidence · deterministic verdicts
              </p>
            )}
          </div>

          <div className="mt-8">
            {run ? (
              <RunView
                run={run}
                onRetest={handleRetest}
                isRetesting={retesting}
                statusNote={statusNote}
              />
            ) : running ? (
              <section className="rounded-[2rem] border border-line bg-panel p-8 shadow-panel sm:p-12">
                <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
                  Measured reliability
                </p>
                <div className="mt-5 flex items-center gap-4 text-lg font-bold text-white">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent" />
                  Running Sentinel…
                </div>
                <p className="mt-4 max-w-xl text-sm leading-6 text-muted">
                  Running the five scenarios against the target over HTTP. Results
                  appear only when the API returns a completed run.
                </p>
              </section>
            ) : (
              <section className="rounded-[2rem] border border-line bg-panel p-8 shadow-panel sm:p-12">
                <p
                  data-testid="empty-score"
                  className="text-xl font-bold text-slate-100 sm:text-2xl"
                >
                  No run yet — press Run Sentinel.
                </p>
                {statusNote ? (
                  <p className="mt-4 max-w-2xl text-sm leading-6 text-fail">
                    {statusNote}
                  </p>
                ) : null}
              </section>
            )}
          </div>

          <div className="mt-12">
            <RunHistory
              runs={runs}
              fallbackRunIds={fallbackRunIds}
              unavailable={historyUnavailable}
              loading={historyLoading}
            />
          </div>
        </>
      )}
    </main>
  );
}
