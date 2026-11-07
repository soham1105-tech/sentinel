"use client";

import { API_UNREACHABLE_MESSAGE } from "@/lib/api";

export function ApiDown() {
  return (
    <div
      data-testid="api-down"
      role="alert"
      className="rounded-2xl border border-fail/30 bg-fail/10 p-6 text-sm leading-7 text-red-100"
    >
      <p>{API_UNREACHABLE_MESSAGE}</p>
      <button
        type="button"
        data-testid="retry-connection"
        onClick={() => window.location.reload()}
        className="mt-4 inline-flex rounded-full border border-fail/40 bg-ink/40 px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-white transition hover:border-accent/50 hover:bg-ink/70"
      >
        Retry connection
      </button>
    </div>
  );
}
