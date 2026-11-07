import Link from "next/link";

import type { RunSummary } from "@/lib/api";
import { scoreLabel } from "@/lib/api";

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
        <h2
          id="history-heading"
          className="mt-1.5 text-2xl font-black tracking-tight sm:text-3xl"
        >
          Run history
        </h2>
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
              {fallbackRunIds.map((runId, index) => (
                <Link
                  key={runId}
                  href={`/runs/${runId}`}
                  className="group rounded-xl border border-line bg-panel/70 p-4 transition hover:border-accent/40 hover:bg-panel"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold text-white">
                        Run #{index + 1}
                        <span className="px-1.5 font-normal text-muted/60">·</span>
                        <span className="font-normal text-muted">Saved locally</span>
                      </p>
                      <p className="mt-1 break-all font-mono text-[10px] text-muted/70">
                        {runId}
                      </p>
                    </div>
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
        <div className="grid gap-3">
          {runs.map((run, index) => (
            <Link
              key={run.run_id}
              href={`/runs/${run.run_id}`}
              className="group rounded-xl border border-line bg-panel/70 p-4 transition hover:border-accent/40 hover:bg-panel sm:p-5"
            >
              <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-sm">
                    <span className="font-bold text-white">Run #{index + 1}</span>
                    <span aria-hidden="true" className="text-muted/50">
                      ·
                    </span>
                    <span className="text-muted">{formatTimestamp(run.created_at)}</span>
                    <span aria-hidden="true" className="text-muted/50">
                      ·
                    </span>
                    <span className="font-mono text-xs font-bold text-fail">
                      {scoreLabel(run.score_before)}
                    </span>
                    <span aria-hidden="true" className="px-0.5 text-muted/50">
                      →
                    </span>
                    <span className="font-mono text-xs font-bold text-pass">
                      {scoreLabel(run.score_after)}
                    </span>
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2">
                    <p className="break-all font-mono text-[10px] text-muted/70">
                      {run.run_id}
                    </p>
                    <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-muted/80">
                      {run.target_version ?? "unknown"}
                    </span>
                  </div>
                </div>
                <span className="shrink-0 text-xs font-semibold text-accent">
                  Open run →
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
