"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function NavLink({
  href,
  children,
  activePrefix,
}: {
  href: string;
  children: ReactNode;
  /** Defaults to an exact pathname match; pass this for a section that owns more than one route (e.g. every /browse/[page]). A plain prefix, not a function — this renders from a Server Component, which can't pass functions to a Client Component prop. */
  activePrefix?: string;
}) {
  const pathname = usePathname();
  const isActive = activePrefix ? pathname.startsWith(activePrefix) : pathname === href;

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      // -my-3 py-3 grows the tap target to meet WCAG 2.2's 24px minimum
      // (SC 2.5.8) without pushing the header row taller — the negative
      // margin cancels the padding's effect on layout, not on hit-testing.
      className={`-my-3 inline-block py-3 font-mono text-[11px] uppercase tracking-widest2 transition-colors hover:text-signal ${
        isActive ? "text-signal" : "text-paper-dim"
      }`}
    >
      {children}
    </Link>
  );
}
