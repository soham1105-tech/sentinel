export function SiteHeader() {
  return (
    <header className="border-b border-line/70 pb-8">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-accent/30 bg-accent/10 text-lg font-black text-accent"
            >
              S
            </span>
            <h1 className="text-2xl font-black tracking-[0.34em] text-white sm:text-3xl">
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
    </header>
  );
}
