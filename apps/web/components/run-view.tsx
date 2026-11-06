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
    <div className="space-y-10">
      <section
        aria-labelledby="score-heading"
        className="rounded-3xl border border-line bg-panel p-6 shadow-[0_28px_80px_rgba(0,0,0,0.24)] sm:p-8"
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p
              id="score-heading"
              className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted"
            >
              Measured reliability
            </p>
            <div
              data-testid="score"
              aria-label={`${run.score_before_label} to ${run.score_after_label}`}
              className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1"
            >
              <span className="text-5xl font-black tracking-tight text-white sm:text-6xl">
                {run.score_before_label}
              </span>
              <span aria-hidden="true" className="text-3xl font-light text-muted/70 sm:text-4xl">
                →
              </span>
              <span className="text-5xl font-black tracking-tight text-accent sm:text-6xl">
                {run.score_after_label}
              </span>
            </div>
            <p className="mt-4 text-sm text-muted">
              {run.tests.length} measured test results · {run.patches.length} guardrail
              patches
            </p>
          </div>

          <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            {onRetest ? (
              <button
                type="button"
                data-testid="retest"
                onClick={onRetest}
                disabled={isRetesting}
                className="rounded-full border border-line bg-white/5 px-5 py-2.5 text-sm font-bold text-white transition hover:border-accent/50 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isRetesting ? "Running retest…" : "Retest"}
              </button>
            ) : null}
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/70">
              {run.target_version_before} → {run.target_version_after}
            </span>
          </div>
        </div>

        {statusNote ? (
          <p className="mt-5 rounded-xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-accent">
            {statusNote}
          </p>
        ) : null}
      </section>

      <section aria-labelledby="evidence-heading" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
              Evidence
            </p>
            <h2 id="evidence-heading" className="mt-2 text-2xl font-black tracking-tight">
              Before and after, scenario by scenario
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            Every verdict is decided by SENTINEL&apos;s deterministic checker. The
            transcripts below are the target&apos;s own replies over HTTP.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
              <h3 className="text-lg font-black text-white">Before — v1</h3>
              <span className="rounded-full border border-fail/25 bg-fail/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-fail">
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

          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
              <h3 className="text-lg font-black text-white">
                After — v2 (patched)
              </h3>
              <span className="rounded-full border border-pass/25 bg-pass/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-pass">
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

      <section aria-labelledby="patches-heading" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-muted">
              Diffs
            </p>
            <h2 id="patches-heading" className="mt-2 text-2xl font-black tracking-tight">
              Patches
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-muted">
            The diagnosis and exact guardrail text for each failed scenario.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {run.patches.map((patch) => {
            const evidence = run.evidence.find(
              (scenario) => scenario.scenario_id === patch.scenario_id,
            );
            return (
              <article
                key={patch.scenario_id}
                data-testid={`patch-${patch.scenario_id}`}
                className="rounded-2xl border border-line bg-panel/80 p-5"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold tracking-[0.16em] text-accent">
                    {patch.scenario_id}
                  </span>
                  <span className="text-sm font-bold text-white">
                    {evidence?.title ?? "Patched scenario"}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-300">{patch.diagnosis}</p>
                <p className="mt-3 rounded-lg border border-line/70 bg-ink/70 px-3 py-2.5 font-mono text-[11px] leading-5 text-slate-200">
                  {patch.patch_text}
                </p>
              </article>
            );
          })}
        </div>
      </section>

      <section
        aria-labelledby="report-heading"
        className="rounded-3xl border border-line bg-panel/70 p-6 sm:p-8"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="report-heading" className="text-2xl font-black tracking-tight">
            Reliability report
          </h2>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted/70">
            {run.narrative_source}
          </span>
        </div>
        <p
          data-testid="report-text"
          className="mt-4 whitespace-pre-wrap text-base leading-8 text-slate-200"
        >
          {run.narrative}
        </p>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-line/70 pt-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted/70">
          <span>Run {run.run_id}</span>
          <span>Method: {run.method}</span>
          <span>Target: {run.target}</span>
        </div>
      </section>
    </div>
  );
}
