"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div>
      <p className="eyebrow mb-3">case file</p>
      <div className="flex flex-wrap items-end gap-x-4 gap-y-2">
        <span className="font-mono text-6xl font-bold tabular-nums text-sev-high">!</span>
        <h1 className="pb-1 text-2xl font-semibold">Something broke rendering this page</h1>
      </div>
      <p className="mt-4 max-w-2xl text-paper-dim">
        This is a client-side error, not a missing page — reloading or trying again usually
        clears it. If it keeps happening, the underlying data or URL may be malformed.
      </p>
      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 border-t border-ink-700 pt-6 font-mono text-xs">
        <button
          type="button"
          onClick={reset}
          className="text-paper underline hover:text-signal"
        >
          Try again
        </button>
        <Link href="/" className="text-paper underline hover:text-signal">
          Back to flagged servers
        </Link>
      </div>
    </div>
  );
}
