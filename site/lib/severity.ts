export function severityColorClass(severity: string): string {
  switch (severity) {
    case "critical":
    case "high":
      return "text-sev-high border-sev-high/40 bg-sev-high/10";
    case "medium":
      return "text-sev-medium border-sev-medium/40 bg-sev-medium/10";
    case "low":
      return "text-sev-low border-sev-low/40 bg-sev-low/10";
    default:
      return "text-paper-dim border-ink-700 bg-ink-800";
  }
}

export function scoreColorClass(score: number): string {
  if (score >= 100) return "text-clear";
  if (score >= 70) return "text-sev-medium";
  return "text-sev-high";
}
