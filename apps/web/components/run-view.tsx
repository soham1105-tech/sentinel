import type { RunReport } from "@/lib/api";
import { ScenarioCard } from "@/components/scenario-card";

type RunViewProps = {
  run: RunReport;
  onRetest?: () => void;
  isRetesting?: boolean;
  statusNote?: string | null;
};

export function RunView({
  run,
  onRetest,
  isRetesting = false,
  statusNote,
}: RunViewProps) {
  return (
    <div className="space-y-9">
      <section
        aria-labelledby="score-heading"
        className="score-reveal relative overflow-hidden rounded-[2rem] border border-line bg-panel p-6 shadow-panel sm:p-8"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-28 h-80 w-80 rounded-full bg-pass/10 blur-3xl"
        />

        <div className="relative flex flex-col gap-8 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <p
                id="score-heading"
                className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted"
              >
                Measured reliability
              </p>
              <span className="rounded-full border border-line bg-white/[0.03] px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                {run.target_version_before} → {run.target_version_after}
              </span>
            </div>

            <div
              data-testid="score"
              aria-label={`${run.score_before_label} to ${run.score_after_label}`}
              className="mt-4 flex flex-wrap items-baseline gap-x-3 gap-y-1"
            >
              <span className="text-5xl font-black tracking-[-0.04em] text-white sm:text-7xl 2xl:text-8xl">
                {run.score_before_label}
              </span>
              <span
                aria-hidden="true"
                className="px-1 text-3xl font-light text-muted/60 sm:text-5xl"
              >
                →
              </span>
              <span className="score-glow text-5xl font-black tracking-[-0.04em] text-accent sm:text-7xl 2xl:text-8xl">
                {run.score_after_label}
              </span>
            </div>

            <div className="mt-6 grid max-w-3xl gap-4 sm:grid-cols-2">
              <div>
                <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-[0.16em]">
                  <span className="text-muted">v1 baseline</span>
                  <span className="text-fail">{run.score_before_percent}%</span>
                </div>
                <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-fail/10 ring-1 ring-inset ring-fail/10">
                  <div
                    data-testid="score-bar-before"
                    className="score-bar-fill h-full rounded-full bg-fail"
                    style={{ width: `${run.score_before_percent}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-[0.16em]">
                  <span className="text-muted">v2 patched</span>
                  <span className="text-pass">{run.score_after_percent}%</span>
                </div>
                <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-pass/10 ring-1 ring-inset ring-pass/10">
                  <div
                    data-testid="score-bar-after"
                    className="score-bar-fill h-full rounded-full bg-pass shadow-[0_0_16px_rgba(34,197,94,0.35)]"
                    style={{ width: `${run.score_after_percent}%` }}
                  />
                </div>
              </div>
            </div>

            <p className="mt-4 text-sm text-muted">
              {run.tests.length} measured test results · {run.patches.length} guardrail
              patches
            </p>
          </div>

          <div className="flex shrink-0 flex-col items-start gap-3 sm:flex-row sm:items-center xl:flex-col xl:items-end">
            {onRetest ? (
              <button
                type="button"
                data-testid="retest"
                onClick={onRetest}
                disabled={isRetesting}
                className="rounded-full bg-white px-6 py-3 text-sm font-black tracking-wide text-ink shadow-[0_8px_28px_rgba(255,255,255,0.08)] transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isRetesting ? "Running retest…" : "Retest"}
              </button>
            ) : null}
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/80">
              Black-box HTTP
            </span>
          </div>
        </div>

        {statusNote ? (
          <p className="relative mt-6 flex items-start gap-2.5 rounded-xl border border-pass/25 bg-pass/10 px-4 py-3 text-sm font-semibold text-pass">
            <span
              aria-hidden="true"
              className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-pass"
            />
            {statusNote}
          </p>
        ) : null}
      </section>

      <section aria-labelledby="evidence-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
              Evidence
            </p>
            <h2
              id="evidence-heading"
              className="mt-1.5 text-2xl font-black tracking-tight sm:text-3xl"
            >
              Before and after, scenario by scenario
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            Every verdict is decided by SENTINEL&apos;s deterministic checker. The
            transcripts below are the target&apos;s own replies over HTTP.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3 border-b border-line/80 pb-3">
              <div className="flex items-center gap-2.5">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-fail" />
                <h3 className="text-lg font-black text-white">Before — v1</h3>
              </div>
              <span className="rounded-full border border-fail/30 bg-fail/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-fail">
                {run.score_before_label}
              </span>
            </div>
            {run.evidence.map((scenario) => (
              <ScenarioCard
                key={`before-${scenario.scenario_id}`}
                side="before"
                scenarioId={scenario.scenario_id}
                title={scenario.title}
                message={scenario.message}
                result={scenario.initial}
                passed={scenario.initial?.passed ?? false}
              />
            ))}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3 border-b border-line/80 pb-3">
              <div className="flex items-center gap-2.5">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-pass" />
                <h3 className="text-lg font-black text-white">
                  After — v2 (patched)
                </h3>
              </div>
              <span className="rounded-full border border-pass/30 bg-pass/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-pass">
                {run.score_after_label}
              </span>
            </div>
            {run.evidence.map((scenario) => {
              const after = scenario.retest ?? scenario.initial;
              return (
                <ScenarioCard
                  key={`after-${scenario.scenario_id}`}
                  side="after"
                  scenarioId={scenario.scenario_id}
                  title={scenario.title}
                  message={scenario.message}
                  result={after}
                  passed={scenario.final_passed}
                />
              );
            })}
          </div>
        </div>
      </section>

      <section aria-labelledby="patches-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
              Diffs
            </p>
            <h2
              id="patches-heading"
              className="mt-1.5 text-2xl font-black tracking-tight sm:text-3xl"
            >
              Patches
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            The diagnosis and exact guardrail text for each failed scenario.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {run.patches.map((patch) => {
            const evidence = run.evidence.find(
              (scenario) => scenario.scenario_id === patch.scenario_id,
            );
            return (
              <article
                key={patch.scenario_id}
                data-testid={`patch-${patch.scenario_id}`}
                className="rounded-xl border border-line/80 border-l-2 border-l-accent/60 bg-panel/70 p-4"
              >
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-xs font-bold tracking-[0.16em] text-accent">
                    {patch.scenario_id}
                  </span>
                  <span className="text-sm font-bold text-white">
                    {evidence?.title ?? "Patched scenario"}
                  </span>
                </div>
                <p className="mt-2.5 text-sm leading-6 text-slate-300">
                  {patch.diagnosis}
                </p>
                <p className="mt-2.5 rounded-lg border border-line/70 bg-ink/70 px-3 py-2.5 font-mono text-[11px] leading-5 text-slate-200">
                  {patch.patch_text}
                </p>
              </article>
            );
          })}
        </div>
      </section>

      <section
        aria-labelledby="report-heading"
        className="rounded-2xl border border-line bg-panel/60 p-6 sm:p-8"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="report-heading" className="text-2xl font-black tracking-tight">
            Reliability report
          </h2>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/80">
            {run.narrative_source}
          </span>
        </div>
        <p
          data-testid="report-text"
          className="mt-4 whitespace-pre-wrap text-base leading-8 text-slate-200"
        >
          {run.narrative}
        </p>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-line/70 pt-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted/80">
          <span>Run {run.run_id}</span>
          <span>Method: {run.method}</span>
          <span>Target: {run.target}</span>
        </div>
      </section>
    </div>
  );
}
