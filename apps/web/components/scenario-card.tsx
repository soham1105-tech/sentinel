import type { TestResult } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

type ScenarioCardProps = {
  scenarioId: string;
  title: string;
  message: string;
  result: TestResult | null;
  passed: boolean;
  side: "before" | "after";
};

export function ScenarioCard({
  scenarioId,
  title,
  message,
  result,
  passed,
  side,
}: ScenarioCardProps) {
  const isFailingBefore = side === "before" && !passed;

  return (
    <article
      data-testid={`scenario-${side}-${scenarioId}`}
      className={[
        "relative overflow-hidden rounded-xl border p-4 shadow-[0_12px_34px_rgba(0,0,0,0.14)]",
        isFailingBefore
          ? "border-fail/30 bg-fail/[0.055]"
          : "border-line/80 bg-panel/80",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-2.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="rounded-md border border-line/80 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-[0.14em] text-muted">
              {scenarioId}
            </span>
            <h3 className="text-sm font-bold text-white sm:text-[15px]">{title}</h3>
          </div>
          <p className="mt-1.5 text-[11px] leading-4 text-muted">{message}</p>
        </div>
        <StatusBadge passed={passed} />
      </div>

      <div
        className={[
          "mt-3 rounded-lg border-y border-r p-4",
          isFailingBefore
            ? "border-fail/20 border-l-4 border-l-fail bg-fail/[0.08] shadow-[inset_0_0_30px_rgba(239,68,68,0.04)]"
            : passed
              ? "border-line/80 border-l-4 border-l-pass/60 bg-ink/70"
              : "border-line/80 border-l-4 border-l-fail/60 bg-ink/70",
        ].join(" ")}
      >
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
          Target reply
        </span>
        <blockquote className="mt-2 whitespace-pre-wrap break-words font-mono text-lg font-semibold leading-7 text-white sm:text-xl">
          {result?.reply
            ? result.reply
            : "No reply was captured by the API for this scenario."}
        </blockquote>
      </div>

      {result?.transcript ? (
        <details className="group mt-3">
          <summary className="cursor-pointer list-none text-[11px] font-semibold text-muted transition hover:text-white">
            <span className="group-open:hidden">View HTTP transcript</span>
            <span className="hidden group-open:inline">Hide HTTP transcript</span>
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-words rounded-lg border border-line/60 bg-black/25 p-3 font-mono text-[10px] leading-5 text-slate-400">
            {result.transcript}
          </pre>
        </details>
      ) : null}
    </article>
  );
}
