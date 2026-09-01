import type { Finding } from "./types";

/**
 * Mirrors the constants in src/mcphound/registry/scoring.py: each finding
 * multiplies the *remaining* score down, worst severity first, so the
 * detail page can show the actual cascade of cuts a score came from
 * instead of a single opaque number.
 */
export const SEVERITY_WEIGHT: Record<string, number> = {
  critical: 0.55,
  high: 0.35,
  medium: 0.15,
  low: 0.05,
};

export const CONFIDENCE_FACTOR: Record<string, number> = {
  high: 1.0,
  medium: 0.7,
  low: 0.4,
};

const SEVERITY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
const CONFIDENCE_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 };

export type CascadeStep = {
  finding: Finding;
  multiplier: number;
  before: number;
  after: number;
};

export function scoreCascade(findings: Finding[]): CascadeStep[] {
  const ordered = [...findings].sort((a, b) => {
    const bySeverity = (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0);
    if (bySeverity !== 0) return bySeverity;
    return (CONFIDENCE_RANK[b.confidence] ?? 0) - (CONFIDENCE_RANK[a.confidence] ?? 0);
  });

  let running = 100;
  return ordered.map((finding) => {
    const weight = SEVERITY_WEIGHT[finding.severity] ?? 0;
    const factor = CONFIDENCE_FACTOR[finding.confidence] ?? 0;
    const multiplier = 1 - weight * factor;
    const before = running;
    running *= multiplier;
    return { finding, multiplier, before, after: running };
  });
}
