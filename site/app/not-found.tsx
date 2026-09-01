import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Not found",
};

export default function NotFound() {
  return (
    <div>
      <p className="eyebrow mb-3">case file</p>
      <div className="flex flex-wrap items-end gap-x-4 gap-y-2">
        <span className="font-mono text-6xl font-bold tabular-nums text-signal">404</span>
        <h1 className="pb-1 text-2xl font-semibold">Nothing on file at this address</h1>
      </div>
      <p className="mt-4 max-w-2xl text-paper-dim">
        This URL doesn&rsquo;t match a server, cluster, or page mcphound tracks. It may have moved,
        or the link was mistyped.
      </p>
      <nav className="mt-8 flex flex-wrap gap-x-6 gap-y-3 border-t border-ink-700 pt-6 font-mono text-xs">
        <Link href="/" className="text-paper underline hover:text-signal">
          Flagged servers
        </Link>
        <Link href="/browse/1" className="text-paper underline hover:text-signal">
          Full registry
        </Link>
        <Link href="/typosquats" className="text-paper underline hover:text-signal">
          Typosquat watchlist
        </Link>
      </nav>
    </div>
  );
}
