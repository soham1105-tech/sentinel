export function SiteHeader() {
  return (
    <header>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-4">
            <span
              aria-hidden="true"
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-accent text-3xl font-black text-ink shadow-accent-glow"
            >
              S
            </span>
            <h1 className="text-3xl font-black tracking-[0.32em] text-white sm:text-4xl">
              SENTINEL
            </h1>
          </div>
          <p className="mt-4 max-w-3xl text-base leading-7 text-muted sm:text-lg">
            The supervisor agent that tests, breaks, and fixes other AI agents before they ship.
          </p>
        </div>
        <span className="w-fit rounded-full border border-line bg-panel px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">
          Agentic Chase · PS05
        </span>
      </div>

      <div className="mt-6 flex items-center gap-3 border-y border-line/70 py-2.5 text-[10px] font-black uppercase tracking-[0.2em] sm:text-[11px]">
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-fail/80" />
        <span className="text-fail">v1 BROKEN</span>
        <span aria-hidden="true" className="px-1 text-muted/50">
          →
        </span>
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full bg-pass shadow-[0_0_10px_rgba(34,197,94,0.75)]"
        />
        <span className="text-pass">v2 FIXED</span>
      </div>
    </header>
  );
}
