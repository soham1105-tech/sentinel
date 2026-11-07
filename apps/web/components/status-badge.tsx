export function StatusBadge({ passed }: { passed: boolean }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full border-2 px-3.5 py-1.5 text-xs font-black tracking-[0.16em]",
        passed
          ? "border-pass/45 bg-pass/15 text-pass"
          : "border-fail/50 bg-fail/15 text-fail",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "h-1.5 w-1.5 rounded-full",
          passed ? "bg-pass" : "bg-fail",
        ].join(" ")}
      />
      {passed ? "PASS" : "FAIL"}
    </span>
  );
}
