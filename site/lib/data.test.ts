import { describe, expect, it } from "vitest";
import { PAGE_SIZE, flaggedServers, pageOfServers, totalPages } from "./data";
import type { IndexEntry } from "./types";

function entry(overrides: Partial<IndexEntry>): IndexEntry {
  return {
    name: "io.github.acme/tool",
    slug: "io.github.acme__tool",
    score: 100,
    finding_count: 0,
    last_scanned_at: "2026-08-30T00:00:00Z",
    ...overrides,
  };
}

describe("flaggedServers", () => {
  it("keeps only servers below a perfect score, worst first", () => {
    const index = [
      entry({ name: "b", slug: "b", score: 100 }),
      entry({ name: "c", slug: "c", score: 76 }),
      entry({ name: "a", slug: "a", score: 94 }),
    ];
    expect(flaggedServers(index).map((e) => e.name)).toEqual(["c", "a"]);
  });

  it("breaks ties by name", () => {
    const index = [
      entry({ name: "z", slug: "z", score: 94 }),
      entry({ name: "a", slug: "a", score: 94 }),
    ];
    expect(flaggedServers(index).map((e) => e.name)).toEqual(["a", "z"]);
  });
});

describe("pagination", () => {
  const index = Array.from({ length: PAGE_SIZE + 1 }, (_, i) =>
    entry({ name: `server-${String(i).padStart(3, "0")}`, slug: `server-${i}` })
  );

  it("computes total pages from index length", () => {
    expect(totalPages(index)).toBe(2);
    expect(totalPages([])).toBe(1);
  });

  it("returns PAGE_SIZE entries sorted by name for page 1", () => {
    const page1 = pageOfServers(index, 1);
    expect(page1).toHaveLength(PAGE_SIZE);
    expect(page1[0].name).toBe("server-000");
  });

  it("returns the remainder on the last page", () => {
    const page2 = pageOfServers(index, 2);
    expect(page2).toHaveLength(1);
    expect(page2[0].name).toBe("server-100");
  });
});
