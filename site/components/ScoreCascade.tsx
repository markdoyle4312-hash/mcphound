import { scoreCascade } from "@/lib/scoring";
import { scoreColorClass } from "@/lib/severity";
import type { Finding } from "@/lib/types";

/**
 * The score isn't a gauge — it's a chain of multiplicative cuts, worst
 * finding first, mirroring src/mcphound/registry/scoring.py's decay model.
 * This renders that chain instead of hiding it behind a single number.
 */
export function ScoreCascade({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="flex items-baseline gap-3 border border-ink-700 bg-ink-900 px-4 py-3">
        <span className="font-mono text-3xl font-bold text-clear tabular-nums">100</span>
        <span className="eyebrow text-clear">no findings — nothing to deduct</span>
      </div>
    );
  }

  const steps = scoreCascade(findings);
  // Derived from the cascade shown above, not a separately-stored score —
  // the ledger must add up to the number it displays.
  const finalScore = Math.round(steps[steps.length - 1].after);

  return (
    <div className="border border-ink-700 bg-ink-900">
      <div className="flex items-baseline justify-between border-b border-ink-700 px-4 py-2">
        <span className="eyebrow">score ledger</span>
        <span className="font-mono text-[11px] text-paper-dim">worst finding first</span>
      </div>
      <ol>
        {steps.map((step, i) => (
          <li
            key={step.finding.rule_id}
            className={`flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm ${
              i > 0 ? "border-t border-ink-800" : ""
            }`}
          >
            <span className="font-mono tabular-nums text-paper-dim">{step.before.toFixed(1)}</span>
            <span className="text-paper-dim">×</span>
            <span className="font-mono tabular-nums text-paper-dim">{step.multiplier.toFixed(3)}</span>
            <span className="text-paper-dim">=</span>
            <span className="font-mono tabular-nums text-paper">{step.after.toFixed(1)}</span>
            <span className="ml-auto font-mono text-xs text-paper-dim">
              {step.finding.rule_id} · {step.finding.severity}/{step.finding.confidence} confidence
            </span>
          </li>
        ))}
      </ol>
      <div className="flex items-baseline justify-between border-t border-ink-700 px-4 py-3">
        <span className="eyebrow">final</span>
        <span className={`font-mono text-2xl font-bold tabular-nums ${scoreColorClass(finalScore)}`}>
          {finalScore}
          <span className="text-xs font-normal text-paper-dim"> /100</span>
        </span>
      </div>
    </div>
  );
}
