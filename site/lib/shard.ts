export const SHARD_COUNT = 64;

export function shardKey(name: string, shardCount: number = SHARD_COUNT): number {
  let hash = 2166136261;
  for (let i = 0; i < name.length; i++) {
    hash ^= name.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % shardCount;
}

export function groupByShard<T>(
  entries: T[],
  nameOf: (entry: T) => string,
  shardCount: number = SHARD_COUNT
): Record<string, T>[] {
  const shards: Record<string, T>[] = Array.from({ length: shardCount }, () => ({}));
  for (const entry of entries) {
    const name = nameOf(entry);
    shards[shardKey(name, shardCount)][name] = entry;
  }
  return shards;
}
