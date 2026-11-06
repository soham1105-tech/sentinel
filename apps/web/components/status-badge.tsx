export function StatusBadge({ passed }: { passed: boolean }) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-black tracking-[0.14em]",
        passed
          ? "border-pass/30 bg-pass/10 text-pass"
          : "border-fail/30 bg-fail/10 text-fail",
      ].join(" ")}
    >
      {passed ? "PASS" : "FAIL"}
    </span>
  );
}
