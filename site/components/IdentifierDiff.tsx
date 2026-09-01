import { charDiff } from "@/lib/diff";

/** Renders the literal character-by-character diff between a known package
 * name and a lookalike identifier — the actual edits, not just the count. */
export function IdentifierDiff({ known, lookalike }: { known: string; lookalike: string }) {
  const ops = charDiff(known, lookalike);

  return (
    <div className="space-y-1 font-mono text-sm leading-relaxed">
      <div className="flex flex-wrap items-start gap-x-0.5">
        <span className="mr-2 shrink-0 text-xs text-paper-dim">known</span>
        {ops.map((op, i) =>
          op.type === "insert" ? null : (
            <span
              key={i}
              className={
                op.type === "equal"
                  ? "text-paper"
                  : "bg-sev-high/20 text-sev-high line-through decoration-2"
              }
            >
              {op.from}
            </span>
          )
        )}
      </div>
      <div className="flex flex-wrap items-start gap-x-0.5">
        <span className="mr-2 shrink-0 text-xs text-paper-dim">seen&nbsp;</span>
        {ops.map((op, i) =>
          op.type === "delete" ? null : (
            <span
              key={i}
              className={
                op.type === "equal" ? "text-paper" : "bg-signal/20 text-signal underline decoration-2"
              }
            >
              {op.to}
            </span>
          )
        )}
      </div>
    </div>
  );
}
