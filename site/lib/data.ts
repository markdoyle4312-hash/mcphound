import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { IndexEntry, ServerDetail, TyposquatCluster } from "./types";

const DATA_DIR = path.join(process.cwd(), "data");

export const PAGE_SIZE = 100;

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(path.join(DATA_DIR, relativePath), "utf-8")) as T;
}

export function loadIndex(): IndexEntry[] {
  return readJson<IndexEntry[]>("index.json");
}

export function loadServer(slug: string): ServerDetail {
  return readJson<ServerDetail>(path.join("servers", `${slug}.json`));
}

export function loadTyposquatClusters(): TyposquatCluster[] {
  if (!existsSync(path.join(DATA_DIR, "typosquat-clusters.json"))) {
    return [];
  }
  return readJson<TyposquatCluster[]>("typosquat-clusters.json");
}

export function flaggedServers(index: IndexEntry[]): IndexEntry[] {
  return index
    .filter((entry) => entry.score < 100)
    .sort((a, b) => a.score - b.score || a.name.localeCompare(b.name));
}

export function totalPages(index: IndexEntry[]): number {
  return Math.max(1, Math.ceil(index.length / PAGE_SIZE));
}

export function pageOfServers(index: IndexEntry[], page: number): IndexEntry[] {
  const sorted = [...index].sort((a, b) => a.name.localeCompare(b.name));
  const start = (page - 1) * PAGE_SIZE;
  return sorted.slice(start, start + PAGE_SIZE);
}
