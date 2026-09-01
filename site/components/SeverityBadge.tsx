import { severityColorClass } from "@/lib/severity";

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wide ${severityColorClass(
        severity
      )}`}
    >
      {severity}
    </span>
  );
}
