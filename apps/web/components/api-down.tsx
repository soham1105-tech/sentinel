import { API_UNREACHABLE_MESSAGE } from "@/lib/api";

export function ApiDown() {
  return (
    <div
      data-testid="api-down"
      role="alert"
      className="rounded-2xl border border-fail/30 bg-fail/10 p-6 text-sm leading-7 text-red-100"
    >
      {API_UNREACHABLE_MESSAGE}
    </div>
  );
}
