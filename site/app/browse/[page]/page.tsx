import Link from "next/link";
import { notFound } from "next/navigation";
import { loadIndex, pageOfServers, totalPages } from "@/lib/data";
import { serverHref } from "@/lib/slug";

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
      <h1 className="text-2xl font-bold mb-6">All scanned servers ({index.length})</h1>
      <table className="w-full text-left border-collapse mb-6">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400">
            <th className="py-2">Server</th>
            <th className="py-2">Score</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.slug} className="border-b border-slate-900">
              <td className="py-2">
                <Link href={serverHref(entry.name)} className="underline">
                  {entry.name}
                </Link>
              </td>
              <td className="py-2">{entry.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <nav className="flex gap-4 text-sm">
        {page > 1 && (
          <Link href={`/browse/${page - 1}`} className="underline">
            Previous
          </Link>
        )}
        <span className="text-slate-500">
          Page {page} of {pages}
        </span>
        {page < pages && (
          <Link href={`/browse/${page + 1}`} className="underline">
            Next
          </Link>
        )}
      </nav>
    </div>
  );
}
