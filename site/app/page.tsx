import type { Metadata } from "next";
import Link from "next/link";
import { flaggedServers, loadIndex } from "@/lib/data";
import { serverHref } from "@/lib/slug";
import { ScoreStamp } from "@/components/ScoreStamp";

function scannedDate(iso: string): string {
  return iso.slice(0, 10);
}

export function generateMetadata(): Metadata {
  const index = loadIndex();
  const flagged = flaggedServers(index);
  return {
    description: `${flagged.length} of ${index.length} watched MCP servers currently score below 100. Worst first, with the exact finding behind every deduction.`,
  };
}

export default function HomePage() {
  const index = loadIndex();
  const flagged = flaggedServers(index);

  return (
    <div>
      <section className="mb-12">
        <p className="eyebrow mb-3">flagged — worst score first</p>
        <div className="flex flex-wrap items-end gap-x-4 gap-y-2">
          <span className="font-mono text-6xl font-bold tabular-nums text-signal">
            {flagged.length}
          </span>
          <h1 className="pb-1 text-2xl font-semibold">
            of {index.length} watched server{index.length === 1 ? "" : "s"} scored below 100
          </h1>
        </div>
        <p className="mt-4 max-w-2xl text-paper-dim">
          Every finding below is static analysis against a public registry entry — hardcoded
          secrets, download-and-execute launchers, typosquats, and more, each mapped to an OWASP
          code.{" "}
          <Link href="/browse/1" className="text-paper underline decoration-ink-700 hover:decoration-signal">
            Browse the full registry
          </Link>
          .
        </p>
      </section>

      {flagged.length === 0 ? (
        <div className="border border-ink-700 bg-ink-900 px-6 py-10 text-center">
          <p className="font-mono text-sm text-clear">Nothing flagged in the current snapshot.</p>
        </div>
      ) : (
        <ol className="divide-y divide-ink-800 border-y border-ink-700">
          {flagged.map((entry, i) => (
            <li key={entry.slug} className="flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
              <span className="w-8 shrink-0 font-mono text-xs text-paper-dim">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="min-w-0 flex-1">
                <Link
                  href={serverHref(entry.name)}
                  className="font-mono text-sm text-paper underline decoration-ink-700 underline-offset-4 hover:decoration-signal"
                >
                  {entry.name}
                </Link>
                <p className="mt-0.5 font-mono text-[11px] text-paper-dim">
                  {entry.finding_count} finding{entry.finding_count === 1 ? "" : "s"} · last
                  scanned {scannedDate(entry.last_scanned_at)}
                </p>
              </div>
              <ScoreStamp score={entry.score} />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
