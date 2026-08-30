#!/usr/bin/env python3
"""Generate a human review packet for ROADMAP.md's W16 spot-check sprint.

Samples a mix of flagged and clean servers from an existing `registry-scan`
run's artifacts (no DB, no network calls — see docs/spot-checks/) and writes
one markdown file with a verdict table plus full finding detail per server,
so a human can hand-verify mcphound's real scores before they're published.

    uv run python scripts/spot_check_sample.py

The sample is stratified, not purely random: MCP-STATIC-003/004 findings are
rare (a handful of servers) but high-value to check by hand, so every server
they hit is included rather than risking a random draw missing them entirely.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mcphound.registry.artifacts import escape_name_component  # noqa: E402

# Rules rare enough that a random sample of "flagged" servers could plausibly
# miss them, but consequential enough to always want a human look.
_RARE_RULES = {"MCP-STATIC-003", "MCP-STATIC-004"}

_GITHUB_NAME_RE = re.compile(r"^io\.github\.([^/]+)/(.+)$")
_NPM_PACKAGE_DETAIL_RE = re.compile(r'npm package "([^"]+)"')


def _verification_link(name: str, findings: list[dict]) -> str | None:
    """Best-effort link for the human to check the server's real source,
    derived only from data already on hand (no network call here)."""
    match = _GITHUB_NAME_RE.match(name)
    if match:
        owner, repo = match.groups()
        return f"https://github.com/{owner}/{repo}"
    for finding in findings:
        detail = finding.get("detail") or ""
        pkg_match = _NPM_PACKAGE_DETAIL_RE.search(detail)
        if pkg_match:
            return f"https://www.npmjs.com/package/{pkg_match.group(1)}"
    return None


def _filename_for(name: str, servers_dir_listing: list[str]) -> str | None:
    """artifacts/index.json rows here predate the "slug" field write_artifacts()
    now emits, so the filename has to be derived the same way the writer does.
    Falls back to a directory scan for the rare case-insensitive-collision
    suffix write_artifacts() appends (see registry/artifacts.py's
    _safe_filename) — that suffix is a content hash we can't recompute here."""
    base = escape_name_component(name)
    exact = f"{base}.json"
    if exact in servers_dir_listing:
        return exact
    prefix = f"{base}-".lower()
    for fname in servers_dir_listing:
        if fname.lower().startswith(prefix) and fname.endswith(".json"):
            return fname
    return None


def _load_server_detail(artifacts_dir: Path, name: str, servers_dir_listing: list[str]) -> dict | None:
    filename = _filename_for(name, servers_dir_listing)
    if filename is None:
        print(f"warning: no per-server artifact found for {name!r}, skipping", file=sys.stderr)
        return None
    path = artifacts_dir / "servers" / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _rule_ids(detail: dict) -> set[str]:
    return {f["rule_id"] for f in detail.get("findings", [])}


def sample(
    index: list[dict],
    artifacts_dir: Path,
    seed: int,
    flagged_sample_size: int,
    clean_sample_size: int,
) -> list[dict]:
    flagged = [row for row in index if row["finding_count"] > 0]
    clean = [row for row in index if row["finding_count"] == 0]
    servers_dir_listing = [p.name for p in (artifacts_dir / "servers").iterdir() if p.suffix == ".json"]

    details_by_name: dict[str, dict] = {}
    rare_rows: list[dict] = []
    common_flagged_rows: list[dict] = []
    for row in flagged:
        detail = _load_server_detail(artifacts_dir, row["name"], servers_dir_listing)
        if detail is None:
            continue
        details_by_name[row["name"]] = detail
        if _rule_ids(detail) & _RARE_RULES:
            rare_rows.append(row)
        else:
            common_flagged_rows.append(row)

    rng = random.Random(seed)
    sampled_common = rng.sample(
        common_flagged_rows, min(flagged_sample_size, len(common_flagged_rows))
    )
    sampled_clean = rng.sample(clean, min(clean_sample_size, len(clean)))

    for row in sampled_clean:
        details_by_name[row["name"]] = _load_server_detail(
            artifacts_dir, row["name"], servers_dir_listing
        ) or {
            "name": row["name"],
            "score": row["score"],
            "finding_count": 0,
            "findings": [],
        }

    selected = rare_rows + sampled_common + sampled_clean
    selected.sort(key=lambda r: (-r["finding_count"], r["name"]))

    packets = []
    for row in selected:
        detail = details_by_name[row["name"]]
        packets.append(
            {
                "name": row["name"],
                "score": detail["score"],
                "finding_count": detail["finding_count"],
                "findings": detail["findings"],
                "link": _verification_link(row["name"], detail["findings"]),
                "group": "rare-rule" if row in rare_rows else ("flagged" if row in sampled_common else "clean"),
            }
        )
    return packets


def render_markdown(
    packets: list[dict],
    total: int,
    flagged_total: int,
    clean_total: int,
    seed: int,
    date_str: str,
) -> str:
    n_rare = sum(1 for p in packets if p["group"] == "rare-rule")
    n_flagged = sum(1 for p in packets if p["group"] == "flagged")
    n_clean = sum(1 for p in packets if p["group"] == "clean")

    lines = [
        f"# W16 Spot-Check Sample — {date_str}",
        "",
        f"Generated by `scripts/spot_check_sample.py --seed {seed}` from "
        f"`artifacts/index.json` ({total} servers scored, {flagged_total} flagged) on {date_str}.",
        "",
        "Purpose: hand-verify a representative sample of mcphound's real registry-scan "
        "output before publishing scores — see ROADMAP.md's W16 credibility gate.",
        "",
        "**Sampling methodology:**",
        f"- All {n_rare} server(s) flagged by the rare rules (`MCP-STATIC-003`/`004`) — too "
        "few to subsample, and the highest-value ones to check by hand.",
        f"- {n_flagged} random server(s) (seed={seed}) out of "
        f"{flagged_total - n_rare} servers flagged only by `MCP-STATIC-007` (missing npm "
        "`repository` field) — the bulk of flagged servers, and the main false-positive risk.",
        f"- {n_clean} random server(s) (seed={seed}) from the {clean_total} clean "
        "(score-100) servers — a false-negative check: did we miss something real?",
        "",
        "Reproducible as long as `artifacts/index.json`/`artifacts/servers/` don't change "
        "between runs — the sample is a deterministic function of the seed and that data.",
        "",
        "## Verdict table",
        "",
        "Fill in **Verdict** as one of: `correct` / `false-positive` / `false-negative` / `uncertain`.",
        "",
        "| # | Server | Score | Rule(s) | Link | Verdict | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(packets, start=1):
        rules = ", ".join(sorted({f["rule_id"] for f in p["findings"]})) or "—"
        link = f"[link]({p['link']})" if p["link"] else "—"
        lines.append(f"| {i} | `{p['name']}` | {p['score']} | {rules} | {link} | TBD | |")

    lines += ["", "## Details", ""]
    for i, p in enumerate(packets, start=1):
        lines.append(f"### {i}. `{p['name']}`")
        lines.append("")
        lines.append(f"- Score: {p['score']} / Finding count: {p['finding_count']}")
        lines.append(f"- Group: {p['group']}")
        lines.append(f"- Link: {p['link'] if p['link'] else 'none derivable — search manually'}")
        if p["findings"]:
            lines.append("- Findings:")
            for f in p["findings"]:
                lines.append(f"  - **{f['rule_id']}** ({f['severity']}/{f['confidence']}, {f['owasp']}) — {f['title']}")
                lines.append(f"    - Detail: {f['detail']}")
                lines.append(f"    - Recommendation: {f['recommendation']}")
        else:
            lines.append("- Findings: none")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=16)
    parser.add_argument("--flagged-sample-size", type=int, default=31)
    parser.add_argument("--clean-sample-size", type=int, default=15)
    parser.add_argument("--artifacts-dir", type=Path, default=REPO_ROOT / "artifacts")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    index = json.loads((args.artifacts_dir / "index.json").read_text(encoding="utf-8"))
    total = len(index)
    flagged_total = sum(1 for r in index if r["finding_count"] > 0)
    clean_total = total - flagged_total

    packets = sample(index, args.artifacts_dir, args.seed, args.flagged_sample_size, args.clean_sample_size)

    date_str = dt.date.today().isoformat()
    out = args.out or REPO_ROOT / "docs" / "spot-checks" / f"w16-{date_str}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(packets, total, flagged_total, clean_total, args.seed, date_str), encoding="utf-8")
    print(f"wrote {len(packets)}-server review packet to {out}")


if __name__ == "__main__":
    main()
