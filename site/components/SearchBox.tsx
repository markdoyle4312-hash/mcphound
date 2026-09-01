"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { serverHref } from "@/lib/slug";
import { scoreColorClass } from "@/lib/severity";

type Entry = [name: string, score: number];

const MAX_RESULTS = 20;

export function SearchBox() {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<Entry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function ensureIndexLoaded() {
    if (index !== null || loading) return;
    setLoading(true);
    fetch("/search-index.json")
      .then((res) => res.json() as Promise<Entry[]>)
      .then(setIndex)
      .catch(() => setIndex([]))
      .finally(() => setLoading(false));
  }

  const trimmed = query.trim().toLowerCase();

  const results = useMemo(() => {
    if (!index || trimmed.length === 0) return [];
    return index
      .filter(([name]) => name.toLowerCase().includes(trimmed))
      .sort(([a], [b]) => {
        const ai = a.toLowerCase().indexOf(trimmed);
        const bi = b.toLowerCase().indexOf(trimmed);
        return ai !== bi ? ai - bi : a.localeCompare(b);
      })
      .slice(0, MAX_RESULTS);
  }, [index, trimmed]);

  const isOpen = trimmed.length > 0;

  return (
    <div ref={containerRef} className="relative">
      <input
        type="search"
        value={query}
        onFocus={ensureIndexLoaded}
        onChange={(event) => {
          setQuery(event.target.value);
          ensureIndexLoaded();
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") setQuery("");
        }}
        placeholder="search servers…"
        aria-label="Search servers by name"
        className="w-36 border border-ink-700 bg-ink-950 px-2 py-1 font-mono text-[11px] text-paper placeholder:text-paper-dim focus:w-56 focus:border-signal focus:outline-none sm:w-44"
      />
      {isOpen && (
        <div className="absolute right-0 top-full z-10 mt-1 max-h-80 w-72 overflow-y-auto border border-ink-700 bg-ink-900 shadow-lg">
          <p className="sr-only" aria-live="polite">
            {loading ? "Loading…" : `${results.length} result${results.length === 1 ? "" : "s"}`}
          </p>
          {loading || index === null ? (
            <p className="px-3 py-2 font-mono text-[11px] text-paper-dim">Loading…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-2 font-mono text-[11px] text-paper-dim">No matches</p>
          ) : (
            <ul>
              {results.map(([name, score]) => (
                <li key={name} className="border-t border-ink-800 first:border-t-0">
                  <Link
                    href={serverHref(name)}
                    onClick={() => setQuery("")}
                    className="flex items-center justify-between gap-3 px-3 py-2 font-mono text-[11px] hover:bg-ink-800"
                  >
                    <span className="truncate text-paper">{name}</span>
                    <span className={`shrink-0 ${scoreColorClass(score)}`}>{score}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
