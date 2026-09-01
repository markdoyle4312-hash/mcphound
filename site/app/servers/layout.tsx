import type { Metadata } from "next";
import type { ReactNode } from "react";

// The actual server name is only known once the client fetches its shard
// (see page.tsx), so this segment gets one fixed, honest title rather than
// a per-server one the static export can't produce.
export const metadata: Metadata = {
  title: "Server lookup",
  description: "Look up the score and findings for a specific MCP server in mcphound's registry.",
};

export default function ServersLayout({ children }: { children: ReactNode }) {
  return children;
}
