"use client";

import { useEffect, useState } from "react";

import { fetchRunSummary, scoreLabel, type RunsSummary } from "@/lib/api";

export function TrendStrip({ refreshKey }: { refreshKey: string }) {
  const [summary, setSummary] = useState<RunsSummary | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const data = await fetchRunSummary();
        if (active) {
          setSummary(data);
        }
      } catch {
        if (active) {
          setSummary(null);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [refreshKey]);

  if (!summary || summary.runs.length === 0) {
    return null;
  }

  const chronological = [...summary.runs].reverse();

  return (
    <div
      data-testid="trend-strip"
      className="flex flex-col gap-3 rounded-2xl border border-line/80 bg-panel/55 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
          Last 10 runs
        </p>
        <p className="mt-1 text-[11px] text-muted/80">
          Headline score · red before · green after
        </p>
      </div>

      <div className="flex items-end gap-2" aria-label="Run trend">
        <div className="flex items-end gap-1.5">
          {chronological.map((run) => {
            const beforeHeight = Math.max(8, (run.score_before / 5) * 100);
            const afterHeight = Math.max(8, (run.score_after / 5) * 100);
            return (
              <div
                key={run.run_id}
                title={`${run.created_at ?? "Unknown time"} · ${scoreLabel(
                  run.score_before,
                )} → ${scoreLabel(run.score_after)}`}
                className="flex h-7 items-end gap-[2px]"
              >
                <span
                  className="w-1.5 rounded-full bg-fail/75"
                  style={{ height: `${beforeHeight}%` }}
                />
                <span
                  className="w-1.5 rounded-full bg-pass"
                  style={{ height: `${afterHeight}%` }}
                />
              </div>
            );
          })}
        </div>
        <span className="font-mono text-[10px] text-muted/80">
          {summary.runs.length}
        </span>
      </div>
    </div>
  );
}
