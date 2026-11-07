export const API_BASE_URL =
  process.env.NEXT_PUBLIC_SENTINEL_API_URL ?? "http://localhost:8000";

export const API_UNREACHABLE_MESSAGE =
  "Sentinel API not reachable at NEXT_PUBLIC_SENTINEL_API_URL — start it with: cd services/sentinel-api && uvicorn main:app --port 8000";

export type TestResult = {
  scenario_id: string;
  title: string;
  message: string;
  expected: string;
  version: string;
  passed: boolean;
  reply: string;
  booked: Record<string, unknown> | null;
  transcript: string;
};

export type Patch = {
  scenario_id: string;
  diagnosis: string;
  patch_text: string;
};

export type SeverityName = "Critical" | "High" | "Medium";

export type SeverityCounts = Record<SeverityName, number>;

export type Failure = {
  scenario_id: string;
  title: string;
  expected: string;
  v1_reply: string;
  diagnosis: string;
  patch_text: string;
  retest_passed: boolean;
  severity?: SeverityName;
  impact?: string;
};

export type Evidence = {
  scenario_id: string;
  title: string;
  message: string;
  expected: string;
  initial: TestResult | null;
  retest: TestResult | null;
  final_passed: boolean;
  severity?: SeverityName | null;
  impact?: string | null;
};

export type SeverityRow = {
  scenario_id: string;
  severity: SeverityName;
  impact: string;
};

export type AdaptiveProbe = {
  scenario_id: string;
  parent_scenario_id: string;
  title: string;
  message: string;
  expected: string;
  initial: TestResult;
  retest: TestResult | null;
  blocked: boolean;
};

export type AdaptiveProbes = {
  generated: number;
  blocked: number;
  total: number;
  label: string;
  items: AdaptiveProbe[];
};

export type RunReport = {
  status?: string;
  run_id: string;
  created_at: string;
  target: string;
  method: string;
  target_version_before: string;
  target_version_after: string;
  score_before: number;
  score_before_percent: number;
  score_before_label: string;
  score_after: number;
  score_after_percent: number;
  score_after_label: string;
  full_suite_before?: number;
  full_suite_before_percent?: number;
  full_suite_before_label?: string;
  full_suite_after?: number;
  full_suite_after_percent?: number;
  full_suite_after_label?: string;
  full_suite_total?: number;
  failures: Failure[];
  full_failures?: Failure[];
  patches: Patch[];
  full_patches?: Patch[];
  tests: TestResult[];
  full_tests?: TestResult[];
  evidence: Evidence[];
  full_evidence?: Evidence[];
  adaptive_probes?: AdaptiveProbes;
  adaptive_results?: TestResult[];
  regression?: string | null;
  regression_checked?: string[];
  regression_results?: TestResult[];
  regression_setup_transcript?: string;
  severity?: {
    before: SeverityCounts;
    after: SeverityCounts;
    rows: SeverityRow[];
  };
  storage: {
    backend?: string;
    path?: string;
    error?: string | null;
  } | null;
  n8n_status: string;
  narrative: string;
  narrative_source: string;
};

export type RunSummary = {
  run_id: string;
  created_at: string | null;
  target_version: string | null;
  score_before: number;
  score_after: number;
};

export type RunTrend = {
  run_id: string;
  created_at: string | null;
  score_before: number;
  score_after: number;
  full_suite_before: number;
  full_suite_after: number;
  full_suite_total: number;
  full_suite_before_label: string;
  full_suite_after_label: string;
  full_suite_before_percent: number;
  full_suite_after_percent: number;
};

export type ScenarioPassRate = {
  scenario_id: string;
  title: string;
  runs: number;
  passed_before: number;
  passed_after: number;
  pass_rate_before: number;
  pass_rate_after: number;
};

export type RunsSummary = {
  runs: RunTrend[];
  per_scenario: ScenarioPassRate[];
};

export type ApiErrorKind = "unreachable" | "not_found" | "unavailable" | "http";

export class SentinelApiError extends Error {
  kind: ApiErrorKind;
  status?: number;

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message);
    this.name = "SentinelApiError";
    this.kind = kind;
    this.status = status;
  }
}

export function isApiUnreachable(error: unknown): boolean {
  return error instanceof SentinelApiError && error.kind === "unreachable";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  const hasBody = init?.body !== undefined;

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(hasBody ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });

    if (response.status === 404) {
      throw new SentinelApiError("not_found", "Run or endpoint not found.", 404);
    }
    if ([405, 501].includes(response.status)) {
      throw new SentinelApiError(
        "unavailable",
        "This API endpoint is unavailable.",
        response.status,
      );
    }
    if (!response.ok) {
      throw new SentinelApiError(
        "http",
        `Sentinel API returned HTTP ${response.status}.`,
        response.status,
      );
    }

    try {
      return (await response.json()) as T;
    } catch {
      throw new SentinelApiError("http", "Sentinel API returned invalid JSON.");
    }
  } catch (error) {
    if (error instanceof SentinelApiError) {
      throw error;
    }
    throw new SentinelApiError("unreachable", API_UNREACHABLE_MESSAGE);
  } finally {
    clearTimeout(timeout);
  }
}

export async function createRun(): Promise<RunReport> {
  return request<RunReport>("/v1/runs", { method: "POST" });
}

export async function fetchRun(runId: string): Promise<RunReport> {
  return request<RunReport>(`/v1/runs/${encodeURIComponent(runId)}`);
}

export async function retestRun(runId: string): Promise<RunReport> {
  return request<RunReport>(`/v1/runs/${encodeURIComponent(runId)}/retest`, {
    method: "POST",
  });
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const runs = await request<RunSummary[]>("/v1/runs");
  if (!Array.isArray(runs)) {
    throw new SentinelApiError("http", "Sentinel API returned an invalid run list.");
  }
  return runs;
}

export async function fetchRunSummary(): Promise<RunsSummary> {
  const summary = await request<RunsSummary>("/v1/runs/summary");
  if (!Array.isArray(summary?.runs) || !Array.isArray(summary?.per_scenario)) {
    throw new SentinelApiError(
      "http",
      "Sentinel API returned an invalid run summary.",
    );
  }
  return summary;
}

export async function pollRun(
  runId: string,
  initial: RunReport,
): Promise<RunReport> {
  let current = initial;
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (current.status === "completed") {
      return current;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
    current = await fetchRun(runId);
  }
  throw new SentinelApiError("http", "Timed out waiting for Sentinel to finish.");
}

const STORAGE_KEY = "sentinel.run.ids";

export function rememberRunId(runId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const existing = getRememberedRunIds();
    const next = [runId, ...existing.filter((id) => id !== runId)].slice(0, 10);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Local history is a convenience only; never block a measured run.
  }
}

export function getRememberedRunIds(): string[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === "string").slice(0, 10);
  } catch {
    return [];
  }
}

export function scoreLabel(score: number, total = 5): string {
  const percent = total > 0 ? Math.round((score / total) * 100) : 0;
  return `${score}/${total} (${percent}%)`;
}
