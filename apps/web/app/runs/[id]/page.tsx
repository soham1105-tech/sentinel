"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiDown } from "@/components/api-down";
import { RunView } from "@/components/run-view";
import { SiteHeader } from "@/components/site-header";
import {
  fetchRun,
  isApiUnreachable,
  rememberRunId,
  retestRun,
  SentinelApiError,
  type RunReport,
} from "@/lib/api";

type RunPageProps = {
  params: { id: string };
};

function block(value: string): string {
  return `\`\`\`text\n${value}\n\`\`\``;
}

function buildMarkdown(run: RunReport): string {
  const evidence = run.full_evidence ?? run.evidence;
  const patches = run.full_patches ?? run.patches;
  const severity = run.severity;
  const adaptive = run.adaptive_probes;
  const lines: string[] = [
    `# SENTINEL report — ${run.run_id}`,
    "",
    `- Created: ${run.created_at}`,
    `- Headline: ${run.score_before_label} → ${run.score_after_label}`,
    `- Full suite: ${run.full_suite_before ?? 0}/${run.full_suite_total ?? evidence.length} → ${run.full_suite_after ?? 0}/${run.full_suite_total ?? evidence.length}`,
    `- Adaptive probes: ${adaptive?.label ?? "0/0 blocked"}`,
    `- Regression: ${run.regression ?? "none"}`,
    `- Target versions: ${run.target_version_before} → ${run.target_version_after}`,
    "",
  ];

  if (severity) {
    lines.push("## Severity");
    lines.push("");
    lines.push("| Severity | Before | After |");
    lines.push("|---|---:|---:|");
    for (const level of ["Critical", "High", "Medium"] as const) {
      lines.push(
        `| ${level} | ${severity.before[level]} | ${severity.after[level]} |`,
      );
    }
    lines.push("");
  }

  lines.push("## Results");
  for (const scenario of evidence) {
    lines.push("");
    lines.push(`### ${scenario.scenario_id} — ${scenario.title}`);
    lines.push("");
    lines.push(`Message: ${scenario.message}`);
    lines.push("");
    lines.push(
      `v1: ${scenario.initial?.passed ? "PASS" : "FAIL"} — ${scenario.initial?.reply ?? "No reply"}`,
    );
    if (scenario.initial?.transcript) {
      lines.push("");
      lines.push(block(scenario.initial.transcript));
    }
    lines.push("");
    const after = scenario.retest ?? scenario.initial;
    lines.push(
      `v2: ${scenario.final_passed ? "PASS" : "FAIL"} — ${after?.reply ?? "No reply"}`,
    );
    if (after?.transcript) {
      lines.push("");
      lines.push(block(after.transcript));
    }
  }

  if (adaptive && adaptive.items.length > 0) {
    lines.push("");
    lines.push("## Adaptive probes");
    for (const probe of adaptive.items) {
      lines.push("");
      lines.push(`### ${probe.scenario_id} — ${probe.title}`);
      lines.push("");
      lines.push(`Message: ${probe.message}`);
      lines.push(
        `v1: ${probe.initial.passed ? "PASS" : "FAIL"} — ${probe.initial.reply}`,
      );
      lines.push(
        `v2: ${probe.retest?.passed ? "PASS" : "FAIL"} — ${probe.retest?.reply ?? "No reply"}`,
      );
      if (probe.initial.transcript) {
        lines.push("");
        lines.push(block(probe.initial.transcript));
      }
      if (probe.retest?.transcript) {
        lines.push("");
        lines.push(block(probe.retest.transcript));
      }
    }
  }

  if (run.regression_results && run.regression_results.length > 0) {
    lines.push("");
    lines.push("## Regression guard");
    for (const result of run.regression_results) {
      lines.push("");
      lines.push(
        `- ${result.scenario_id}: ${result.passed ? "PASS" : "FAIL"} — ${result.reply}`,
      );
      if (result.transcript) {
        lines.push("");
        lines.push(block(result.transcript));
      }
    }
  }

  lines.push("");
  lines.push("## Patches");
  for (const patch of patches) {
    lines.push("");
    lines.push(`### ${patch.scenario_id}`);
    lines.push("");
    lines.push(patch.diagnosis);
    lines.push("");
    lines.push(block(patch.patch_text));
  }

  lines.push("");
  lines.push("## Reliability report");
  lines.push("");
  lines.push(run.narrative);
  lines.push("");
  return lines.join("\n");
}

function downloadReport(run: RunReport): void {
  const blob = new Blob([buildMarkdown(run)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `sentinel-${run.run_id}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function RunPage({ params }: RunPageProps) {
  const [run, setRun] = useState<RunReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiDown, setApiDown] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retesting, setRetesting] = useState(false);
  const [statusNote, setStatusNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setApiDown(false);
      setNotFound(false);
      setLoadError(null);
      try {
        const loaded = await fetchRun(params.id);
        if (active) {
          setRun(loaded);
        }
      } catch (error) {
        if (!active) {
          return;
        }
        if (isApiUnreachable(error)) {
          setApiDown(true);
        } else if (
          error instanceof SentinelApiError &&
          error.kind === "not_found"
        ) {
          setNotFound(true);
        } else {
          setLoadError(
            error instanceof Error ? error.message : "Could not load this run.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [params.id]);

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
    <main className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 sm:py-12">
      <SiteHeader />

      {apiDown ? (
        <div className="mt-10">
          <ApiDown />
        </div>
      ) : loading ? (
        <div className="mt-10 rounded-3xl border border-line bg-panel p-8">
          <div className="flex items-center gap-3 text-sm font-semibold text-muted">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
            Loading run…
          </div>
        </div>
      ) : notFound ? (
        <div className="mt-10 rounded-3xl border border-line bg-panel p-8">
          <p className="text-xl font-bold text-white">Run not found.</p>
          <p className="mt-3 text-sm text-muted">
            The API has no record of <span className="font-mono">{params.id}</span>.
          </p>
          <Link
            href="/"
            className="mt-5 inline-flex rounded-full border border-line px-4 py-2 text-sm font-semibold text-white transition hover:border-accent/40"
          >
            Back to dashboard
          </Link>
        </div>
      ) : loadError ? (
        <div className="mt-10 rounded-3xl border border-fail/30 bg-fail/10 p-8">
          <p className="text-sm leading-6 text-red-100">{loadError}</p>
          <Link
            href="/"
            className="mt-5 inline-flex rounded-full border border-line px-4 py-2 text-sm font-semibold text-white transition hover:border-accent/40"
          >
            Back to dashboard
          </Link>
        </div>
      ) : run ? (
        <div data-testid="run-detail" className="mt-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link
              href="/"
              className="inline-flex text-xs font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-white"
            >
              ← Back to dashboard
            </Link>
            <button
              type="button"
              data-testid="download-report"
              onClick={() => downloadReport(run)}
              className="rounded-full border border-line bg-white/5 px-4 py-2 text-xs font-bold text-white transition hover:border-accent/50 hover:bg-white/10"
            >
              Download report (.md)
            </button>
          </div>
          <RunView
            run={run}
            onRetest={handleRetest}
            isRetesting={retesting}
            statusNote={statusNote}
          />
        </div>
      ) : null}
    </main>
  );
}
