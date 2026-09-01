import { describe, expect, it } from "vitest";
import { SHARD_COUNT, groupByShard, shardKey } from "./shard";

describe("shardKey", () => {
  it("is deterministic for the same name", () => {
    expect(shardKey("io.github.acme/tool")).toBe(shardKey("io.github.acme/tool"));
  });

  it("stays within [0, shardCount)", () => {
    const names = Array.from({ length: 500 }, (_, i) => `server-${i}`);
    for (const name of names) {
      const key = shardKey(name, 16);
      expect(key).toBeGreaterThanOrEqual(0);
      expect(key).toBeLessThan(16);
    }
  });

  it("distributes distinct names across more than a handful of buckets", () => {
    const names = Array.from({ length: 500 }, (_, i) => `server-${i}`);
    const buckets = new Set(names.map((name) => shardKey(name, SHARD_COUNT)));
    expect(buckets.size).toBeGreaterThan(10);
  });
});

describe("groupByShard", () => {
  type Entry = { name: string; value: number };

  it("preserves every input entry across exactly one shard each", () => {
    const entries: Entry[] = Array.from({ length: 50 }, (_, i) => ({
      name: `server-${i}`,
      value: i,
    }));
    const shards = groupByShard(entries, (e) => e.name, 8);
    expect(shards).toHaveLength(8);
    const flattened = shards.flatMap((shard) => Object.values(shard));
    expect(flattened).toHaveLength(entries.length);
    expect(new Set(flattened.map((e) => e.value))).toEqual(new Set(entries.map((e) => e.value)));
  });

  it("last write wins on a same-name collision within one call", () => {
    const entries: Entry[] = [
      { name: "dup", value: 1 },
      { name: "dup", value: 2 },
    ];
    const shards = groupByShard(entries, (e) => e.name, 4);
    const found = shards.find((shard) => "dup" in shard);
    expect(found?.dup.value).toBe(2);
  });
});
