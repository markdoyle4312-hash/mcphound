# mcphound detection rule catalog

Generated from `src/mcphound/rules/*.yaml` by `scripts/generate_rule_docs.py` —
do not hand-edit; run the generator after changing a rule instead. Every rule
maps to an OWASP LLM Top 10 (`LLMxx`) or Agentic/MCP Top 10 (`ASTxx`) code; see
`.claude/skills/rule-authoring/SKILL.md` for how to add one.

| Rule | Title | Severity | Confidence | OWASP | Network? |
|---|---|---|---|---|---|
| [`MCP-STATIC-001`](#mcp-static-001) | Hardcoded secret in MCP server environment | high | high | LLM02 |  |
| [`MCP-STATIC-002`](#mcp-static-002) | Remote code download-and-execute in launch command | critical | high | AST04 |  |
| [`MCP-STATIC-003`](#mcp-static-003) | Over-broad host/filesystem permissions in launch command | high | medium | LLM08 |  |
| [`MCP-STATIC-004`](#mcp-static-004) | Unpinned or @latest package version in launch command | medium | medium | AST04 |  |
| [`MCP-STATIC-005`](#mcp-static-005) | Tool-description injection markers in server config | critical | medium | LLM01 |  |
| [`MCP-STATIC-006`](#mcp-static-006) | Typosquat of a known MCP server package name | high | medium | AST04 |  |
| [`MCP-STATIC-007`](#mcp-static-007) | Package has no discoverable source repository | medium | low | AST04 | yes |


## MCP-STATIC-001

**Hardcoded secret in MCP server environment**

- Severity: `high`
- Confidence: `high`
- OWASP mapping: `LLM02`
- Phase: `static`
- Network-dependent: no
- Detection: Regex against `env`

A literal credential/token appears in an MCP server env block. Committed credentials leak through git, CI logs, and shared machine configs. Use environment variable expansion (${VAR}) instead.

**Recommendation:** Replace with "${VAR}" expansion; rotate the leaked credential; add gitleaks.

References:
- https://www.owasp.org/index.php/OWASP_Top_10_for_LLM_Applications

---

## MCP-STATIC-002

**Remote code download-and-execute in launch command**

- Severity: `critical`
- Confidence: `high`
- OWASP mapping: `AST04`
- Phase: `static`
- Network-dependent: no
- Detection: Regex against `command`

The server launch command pipes a remote download straight into a shell (curl|sh / wget|sh), executing unversioned remote code at every startup — the rug-pull / supply-chain kill chain in one line.

**Recommendation:** Install a pinned package from a registry; vendor the script; verify signatures.

References:
- https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/

---

## MCP-STATIC-003

**Over-broad host/filesystem permissions in launch command**

- Severity: `high`
- Confidence: `medium`
- OWASP mapping: `LLM08`
- Phase: `static`
- Network-dependent: no
- Detection: Regex against `command`

The server launch command requests host-level or filesystem-root access (privileged containers, host networking, root volume mounts, disabled browser sandboxing, or a bare "/" path argument) — violating least-privilege and giving a compromised server full host reach instead of a scoped one.

**Recommendation:** Scope volume mounts/paths to the minimum directory needed, drop --privileged/--network=host/--cap-add=ALL, and keep browser sandboxing enabled.

References:
- https://labs.cloudsecurityalliance.org/agentic/agentic-mcp-security-best-practices-v1/

---

## MCP-STATIC-004

**Unpinned or @latest package version in launch command**

- Severity: `medium`
- Confidence: `medium`
- OWASP mapping: `AST04`
- Phase: `static`
- Network-dependent: no
- Detection: Regex against `command`

An npx/uvx launch command references a package with no version pin (or the mutable "@latest" tag), or a "docker run" launch command references an image with no tag (implicit ":latest") or a floating, non-semver tag. The exact code that runs can change between invocations without review — the same rug-pull risk class as unsigned install scripts, just via registry mutation instead of a script. A digest-pinned image ("@sha256:...") or an explicit numeric version tag is not flagged.

**Recommendation:** Pin an exact version, e.g. "npx -y pkg@1.2.3" or "docker run image:1.2.3" (or "image@sha256:..." for a digest pin); bump deliberately and note the bump in the commit message.

References:
- https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/

---

## MCP-STATIC-005

**Tool-description injection markers in server config**

- Severity: `critical`
- Confidence: `medium`
- OWASP mapping: `LLM01`
- Phase: `static`
- Network-dependent: no
- Detection: Regex against `raw`

The server's config entry contains hidden HTML/XML comment blocks, zero-width Unicode characters, or exfiltration-imperative phrasing ("ignore previous instructions", "send ... to", "do not tell the user"). These are the documented tool-poisoning markers used to plant instructions a human reviewer won't see but an LLM reading the tool/description text will.

**Recommendation:** Remove hidden/zero-width content and imperative phrasing from server metadata; review the server's actual tool descriptions via the MCP Inspector before trusting it.

References:
- https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks

---

## MCP-STATIC-006

**Typosquat of a known MCP server package name**

- Severity: `high`
- Confidence: `medium`
- OWASP mapping: `AST04`
- Phase: `static`
- Network-dependent: no
- Detection: Levenshtein distance ≤ 2 from a name in `known_servers.yaml`, checked against `command`

The npx/uvx package name launched by this server is one or two edits away from a well-known legitimate MCP server package, but not an exact match — the classic typosquat pattern (extra/missing/transposed characters) used to trick installers into running a lookalike package instead of the real one.

**Recommendation:** Double-check the exact package name against the official registry/npm page before installing; pin the verified name and version.

References:
- https://appsentinels.ai/blog/mcp-supply-chain-security-how-malicious-mcp-servers-are-infiltrating-enterprise-ai-environments/

---

## MCP-STATIC-007

**Package has no discoverable source repository**

- Severity: `medium`
- Confidence: `low`
- OWASP mapping: `AST04`
- Phase: `static`
- Network-dependent: yes, `--deep` only
- Detection: npm registry lookup for the launched package's `repository` field (network)

The npx- or uvx-launched package's registry metadata has no discoverable source repository — npm's "repository" field, or a PyPI project_urls entry labeled Source/Repository/Code/GitHub/GitLab — so there's no public source to audit, review, or diff against a future version. ~15% of registry MCP servers ship with no source repo (Nimblebrain, 2026). A missing repo isn't proof of malice (small/private packages omit it too), so this is a low-confidence signal, not a hard block.

**Recommendation:** Prefer packages with a public, reviewable source repository; if you maintain this package, add a "repository" field to package.json (npm) or a Source/Repository project URL (PyPI).

References:
- https://nimblebrain.ai/mcp/mcp-security/state-of-mcp-security/
