import Link from "next/link";
import { notFound } from "next/navigation";
import { loadIndex, pageOfServers, totalPages } from "@/lib/data";
import { serverHref } from "@/lib/slug";
import { ScoreStamp } from "@/components/ScoreStamp";

export function generateStaticParams() {
  const pages = totalPages(loadIndex());
  return Array.from({ length: pages }, (_, i) => ({ page: String(i + 1) }));
}

export default async function BrowsePage({ params }: { params: Promise<{ page: string }> }) {
  const { page: pageParam } = await params;
  const index = loadIndex();
  const page = Number(pageParam);
  const pages = totalPages(index);
  if (!Number.isInteger(page) || page < 1 || page > pages) {
    notFound();
  }
  const entries = pageOfServers(index, page);

  return (
    <div>
      <p className="eyebrow mb-3">full registry</p>
      <h1 className="mb-8 text-2xl font-semibold">{index.length} servers under watch</h1>

      <div className="overflow-x-auto border border-ink-700">
        <table className="w-full min-w-[28rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-ink-700 bg-ink-900 font-mono text-[11px] uppercase tracking-widest2 text-paper-dim">
              <th className="px-4 py-2.5 font-medium">Server</th>
              <th className="px-4 py-2.5 font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-800">
            {entries.map((entry) => (
              <tr key={entry.slug}>
                <td className="px-4 py-2.5">
                  <Link
                    href={serverHref(entry.name)}
                    className="font-mono text-paper underline decoration-ink-700 underline-offset-4 hover:decoration-signal"
                  >
                    {entry.name}
                  </Link>
                </td>
                <td className="px-4 py-2.5">
                  <ScoreStamp score={entry.score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <nav className="mt-6 flex items-center gap-4 font-mono text-xs">
        {page > 1 ? (
          <Link href={`/browse/${page - 1}`} className="text-paper underline hover:text-signal">
            ← previous
          </Link>
        ) : (
          <span className="text-ink-700">← previous</span>
        )}
        <span className="text-paper-dim">
          page {page} of {pages}
        </span>
        {page < pages ? (
          <Link href={`/browse/${page + 1}`} className="text-paper underline hover:text-signal">
            next →
          </Link>
        ) : (
          <span className="text-ink-700">next →</span>
        )}
      </nav>
    </div>
  );
}
