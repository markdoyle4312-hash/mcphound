import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadIndex, loadServer } from "../lib/data.ts";
import { groupByShard, SHARD_COUNT } from "../lib/shard.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(here, "..", "public", "data");

const index = loadIndex();
const servers = index.map((entry) => loadServer(entry.slug));
const shards = groupByShard(servers, (server) => server.name, SHARD_COUNT);

if (existsSync(outDir)) {
  rmSync(outDir, { recursive: true, force: true });
}
mkdirSync(outDir, { recursive: true });
shards.forEach((shard, i) => {
  writeFileSync(path.join(outDir, `shard-${i}.json`), JSON.stringify(shard));
});
console.log(`wrote ${SHARD_COUNT} server-data shards (${servers.length} servers) to ${outDir}`);
