"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { RunReport, RunSummary } from "@/lib/api";
import { fetchRun, scoreLabel } from "@/lib/api";
import { SeveritySummary } from "@/components/severity-summary";

type RunHistoryProps = {
  runs: RunSummary[] | null;
  fallbackRunIds: string[];
  unavailable: boolean;
  loading: boolean;
};

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Time unavailable";
  }
  return value.replace("T", " ").replace("Z", "").slice(0, 19);
}

export function RunHistory({
  runs,
  fallbackRunIds,
  unavailable,
  loading,
}: RunHistoryProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedRuns, setSelectedRuns] = useState<RunReport[]>([]);
  const [comparisonError, setComparisonError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (selectedIds.length !== 2) {
      setSelectedRuns([]);
      setComparisonError(null);
      return () => {
        active = false;
      };
    }

    setComparisonError(null);
    Promise.all(selectedIds.map((runId) => fetchRun(runId)))
      .then((loaded) => {
        if (active) {
          setSelectedRuns(loaded);
        }
      })
      .catch(() => {
        if (active) {
          setSelectedRuns([]);
          setComparisonError("Could not load both runs for comparison.");
        }
      });

    return () => {
      active = false;
    };
  }, [selectedIds]);

  function toggleRun(runId: string) {
    setSelectedIds((current) => {
      if (current.includes(runId)) {
        return current.filter((id) => id !== runId);
      }
      if (current.length >= 2) {
        return current;
      }
      return [...current, runId];
    });
  }

  const runNumber = (runId: string) => {
    const index = runs?.findIndex((run) => run.run_id === runId) ?? -1;
    return index >= 0 ? index + 1 : null;
  };

  return (
    <section
      aria-labelledby="history-heading"
      data-testid="run-history"
      className="space-y-5"
    >
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
          Audit trail
        </p>
        <h2 id="history-heading" className="mt-2 text-2xl font-black tracking-tight">
          Run history
        </h2>
        <p className="mt-2 text-sm text-muted">
          Ticking two runs opens a side-by-side comparison.
        </p>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-line bg-panel/60 p-5 text-sm text-muted">
          Loading run history…
        </p>
      ) : unavailable ? (
        <div className="space-y-3">
          <p className="rounded-xl border border-line bg-panel/60 px-4 py-3 text-sm text-muted">
            API run history is unavailable. Showing run IDs saved in this browser.
          </p>
          {fallbackRunIds.length === 0 ? (
            <p className="text-sm text-muted">No local run IDs yet.</p>
          ) : (
            <div className="grid gap-3">
              {fallbackRunIds.map((runId) => (
                <Link
                  key={runId}
                  href={`/runs/${runId}`}
                  className="group rounded-2xl border border-line bg-panel/70 p-4 transition hover:border-accent/40 hover:bg-panel"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="break-all font-mono text-xs text-slate-200">
                      {runId}
                    </span>
                    <span className="text-xs font-semibold text-accent">
                      Open run →
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      ) : !runs || runs.length === 0 ? (
        <p className="rounded-2xl border border-line bg-panel/60 p-5 text-sm text-muted">
          No runs yet. Press Run Sentinel to create the first measured run.
        </p>
      ) : (
        <div className="space-y-5">
          <div className="grid gap-3">
            {runs.map((run) => {
              const selected = selectedIds.includes(run.run_id);
              const disabled = selectedIds.length >= 2 && !selected;
              return (
                <div
                  key={run.run_id}
                  className={[
                    "flex items-start gap-3 rounded-2xl border bg-panel/70 p-4 transition sm:p-5",
                    selected
                      ? "border-accent/50 bg-panel"
                      : "border-line hover:border-accent/40 hover:bg-panel",
                  ].join(" ")}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={disabled}
                    onChange={() => toggleRun(run.run_id)}
                    aria-label={`Select run ${run.run_id}`}
                    className="mt-1.5 h-4 w-4 shrink-0 cursor-pointer rounded border-line bg-ink accent-accent disabled:cursor-not-allowed disabled:opacity-40"
                  />
                  <Link
                    href={`/runs/${run.run_id}`}
                    className="group min-w-0 flex-1"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="font-mono text-xs font-semibold text-slate-200">
                            {run.run_id}
                          </span>
                          <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                            {run.target_version ?? "unknown"}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-muted">
                          {formatTimestamp(run.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-mono text-xs text-slate-300">
                          {scoreLabel(run.score_before)} → {scoreLabel(run.score_after)}
                        </span>
                        <span className="text-xs font-semibold text-accent">
                          Open run →
                        </span>
                      </div>
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>

          {selectedIds.length > 0 ? (
            <section
              data-testid="run-comparison"
              className="rounded-2xl border border-line bg-panel/70 p-5"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-black text-white">Compare runs</h3>
                <button
                  type="button"
                  onClick={() => setSelectedIds([])}
                  className="text-xs font-semibold text-muted transition hover:text-white"
                >
                  Clear selection
                </button>
              </div>

              {selectedIds.length < 2 ? (
                <p className="mt-3 text-sm text-muted">
                  Select one more run to compare.
                </p>
              ) : comparisonError ? (
                <p className="mt-3 text-sm text-fail">{comparisonError}</p>
              ) : selectedRuns.length < 2 ? (
                <p className="mt-3 text-sm text-muted">Loading comparison…</p>
              ) : (
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {selectedRuns.map((run, index) => {
                    const total =
                      run.full_suite_total ??
                      run.full_evidence?.length ??
                      run.evidence.length;
                    const number = runNumber(run.run_id);
                    return (
                      <article
                        key={run.run_id}
                        data-testid={`compare-run-${index + 1}`}
                        className="rounded-xl border border-line bg-ink/40 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-black text-white">
                              Run {number ? `#${number}` : "selected"}
                            </p>
                            <p className="mt-1 break-all font-mono text-[10px] text-muted/80">
                              {run.run_id}
                            </p>
                          </div>
                          <Link
                            href={`/runs/${run.run_id}`}
                            className="shrink-0 text-xs font-semibold text-accent"
                          >
                            Open →
                          </Link>
                        </div>
                        <div className="mt-4 space-y-2">
                          <div className="flex items-baseline justify-between gap-3">
                            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">
                              Headline
                            </span>
                            <span className="font-mono text-xs text-slate-200">
                              {run.score_before_label} → {run.score_after_label}
                            </span>
                          </div>
                          <div className="flex items-baseline justify-between gap-3">
                            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">
                              Full suite
                            </span>
                            <span className="font-mono text-xs text-slate-200">
                              {run.full_suite_before ?? 0}/{total} →{" "}
                              {run.full_suite_after ?? 0}/{total}
                            </span>
                          </div>
                        </div>
                        <div className="mt-4">
                          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-muted">
                            Severity before → after
                          </p>
                          {run.severity ? (
                            <SeveritySummary
                              before={run.severity.before}
                              after={run.severity.after}
                              compact
                            />
                          ) : (
                            <p className="text-xs text-muted">
                              Severity not recorded for this run.
                            </p>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          ) : null}
        </div>
      )}
    </section>
  );
}
