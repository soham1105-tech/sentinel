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
    <main className="relative isolate mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 sm:py-12">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px] bg-[radial-gradient(ellipse_at_top,rgba(110,231,183,0.07),transparent_62%)]"
      />
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
          <Link
            href="/"
            className="inline-flex text-xs font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-white"
          >
            ← Back to dashboard
          </Link>
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
