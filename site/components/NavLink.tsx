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
      className={`font-mono text-[11px] uppercase tracking-widest2 transition-colors hover:text-signal ${
        isActive ? "text-signal" : "text-paper-dim"
      }`}
    >
      {children}
    </Link>
  );
}
