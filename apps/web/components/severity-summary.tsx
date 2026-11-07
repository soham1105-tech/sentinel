import type { SeverityCounts, SeverityName } from "@/lib/api";

const LEVELS: SeverityName[] = ["Critical", "High", "Medium"];

const LEVEL_CLASS: Record<SeverityName, string> = {
  Critical: "text-fail",
  High: "text-amber-300",
  Medium: "text-yellow-200",
};

export function SeveritySummary({
  before,
  after,
  compact = false,
}: {
  before: SeverityCounts;
  after: SeverityCounts;
  compact?: boolean;
}) {
  return (
    <div
      className={
        compact
          ? "space-y-1.5"
          : "grid gap-2 sm:grid-cols-3"
      }
    >
      {LEVELS.map((level) => (
        <div
          key={level}
          className="flex items-center justify-between gap-3 rounded-lg border border-line/70 bg-ink/45 px-3 py-2"
        >
          <span className={`text-[10px] font-black uppercase tracking-[0.14em] ${LEVEL_CLASS[level]}`}>
            {level}
          </span>
          <span className="font-mono text-xs text-slate-200">
            {before[level]}
            <span className="px-1 text-muted/50">→</span>
            {after[level]}
          </span>
        </div>
      ))}
    </div>
  );
}
