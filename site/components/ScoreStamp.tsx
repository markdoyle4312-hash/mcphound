import { scoreColorClass } from "@/lib/severity";

/** Compact score readout for list rows, where only the final number is known. */
export function ScoreStamp({ score }: { score: number }) {
  return (
    <span className={`font-mono text-lg font-bold tabular-nums ${scoreColorClass(score)}`}>
      {score}
      <span className="text-xs font-normal text-paper-dim">/100</span>
    </span>
  );
}
