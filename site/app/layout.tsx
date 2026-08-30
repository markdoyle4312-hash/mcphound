import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "mcphound — MCP server reputation",
  description: "Security scores for public Model Context Protocol servers.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <header className="border-b border-slate-800 px-6 py-4">
          <Link href="/" className="font-semibold text-lg">
            mcphound
          </Link>
        </header>
        <main className="px-6 py-8 max-w-4xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
