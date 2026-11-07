import type { SeverityName, TestResult } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

type ScenarioCardProps = {
  scenarioId: string;
  title: string;
  message: string;
  result: TestResult | null;
  passed: boolean;
  side: "before" | "after";
  severity?: SeverityName | null;
};

const SEVERITY_CLASS: Record<SeverityName, string> = {
  Critical: "border-fail/40 bg-fail/10 text-fail",
  High: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  Medium: "border-yellow-300/30 bg-yellow-300/10 text-yellow-200",
};

export function ScenarioCard({
  scenarioId,
  title,
  message,
  result,
  passed,
  side,
  severity,
}: ScenarioCardProps) {
  return (
    <article
      data-testid={`scenario-${side}-${scenarioId}`}
      className={[
        "rounded-2xl border bg-panel/80 p-5 shadow-[0_18px_50px_rgba(0,0,0,0.16)]",
        passed ? "border-pass/20" : "border-fail/25",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-xs font-bold tracking-[0.16em] text-muted">
              {scenarioId}
            </span>
            <h3 className="text-sm font-bold text-white sm:text-base">{title}</h3>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted">{message}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <StatusBadge passed={passed} />
          {!passed && severity ? (
            <span
              data-testid={`severity-badge-${side}-${scenarioId}`}
              className={[
                "rounded-full border px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.14em]",
                SEVERITY_CLASS[severity],
              ].join(" ")}
            >
              {severity}
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-line/80 bg-ink/70 p-4">
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
          Target reply
        </span>
        <blockquote className="mt-2.5 whitespace-pre-wrap break-words font-mono text-[13px] leading-6 text-slate-100">
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
