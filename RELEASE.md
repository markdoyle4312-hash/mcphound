Release runbook — first PyPI publish (v0.1.0)

**Historical / one-time bootstrap doc.** This covers the v0.1.0 first-ever
publish steps (PyPI account setup, wheel-contents verification, TestPyPI
dry-run) — already done. For every release after v0.1.0, use
`.claude/skills/release/SKILL.md` instead; it's the current, repeatable
checklist. Kept here as a record of the one-time setup steps.

Work through top to bottom. The whole thing takes ~15 minutes.

1. Fix the placeholders BEFORE building
 Repo name / URLs are real. Search the repo for your-org and replace with your GitHub org/name:

output.py
 → informationUri

pyproject.toml
 → [project.urls]
 Package name is available on PyPI. Check https://pypi.org/project/mcphound/ in a browser (404 = free) or:
PowerShell

uv pip index versions mcphound
If taken, rename in
pyproject.toml
 now — renaming after your first publish means a second, permanent package name forever.
2. Enrich package metadata (one-time)
Fill in
pyproject.toml
:

 authors = [{ name = "...", email = "..." }]
 [project.urls]: Homepage / Repository / Issues / Changelog
 classifiers (Python 3.12+, Apache-2.0, intended audience)
 keywords = ["mcp", "security", "supply-chain", "ai-agents", "sarif"]
3. Build and verify the WHEEL CONTENTS (critical)
Your YAML detection rules live inside src/mcphound/rules/. If they aren't
packed into the wheel, installed users get a scanner with zero rules —
tests pass locally but the published package is broken.

Bash

uv build
# inspect the wheel — you MUST see the .yaml rule files listed:
python -m zipfile -l dist/mcphound-0.1.0-py3-none-any.whl | findstr yaml
Expected:
MCP-STATIC-001.yaml
 and 002.yaml in the listing.
If missing, add to
pyproject.toml
:

toml

[tool.hatch.build.targets.wheel.force-include]
"src/mcphound/rules" = "mcphound/rules"
4. Test the BUILT ARTIFACT in a clean environment
Bash

uv venv /tmp/wheel-test
/tmp/wheel-test/Scripts/pip install dist/mcphound-0.1.0-py3-none-any.whl   # PowerShell
# then from a DIFFERENT directory (so it uses the installed package, not the repo):
cd .. && /tmp/wheel-test/Scripts/mcphound inspect
/tmp/wheel-test/Scripts/mcphound scan <path-to-some-.mcp.json> --json
Confirm: CLI runs, rules load (findings appear for a secret fixture), no import errors.

5. Dry-run publish to TestPyPI
Bash

# one-time: create account at test.pypi.org, create an API token
$env:UV_PUBLISH_TOKEN = "pypi-testtoken-..."
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
Install from TestPyPI in the clean venv and smoke-test again.

6. Publish to PyPI for real
Bash

# one-time: pypi.org account with 2FA enabled → create a SCOPED API token
# (scope it to just this project after the first upload creates it;
#  first upload needs an account-scoped token)
$env:UV_PUBLISH_TOKEN = "pypi-..."
uv publish dist/*
Then verify: uvx mcphound --help runs on a clean machine.

Future improvement (not v0.1): set up GitHub OIDC "Trusted Publisher" so
tags publish automatically without long-lived tokens.

7. Tag and release on GitHub
Bash

git tag -a v0.1.0 -m "v0.1.0: static MCP config scanner"
git push origin v0.1.0
 GitHub Release with notes: what v0.1 does, install command, rule list with OWASP mappings, "not yet: dynamic analysis/reputation site" expectations.
 Update the homepage/repo description and topics.
8. Launch (Roadmap W6 — same day if possible)
 Show HN: title like "Show HN: mcphound – scan your Claude/Cursor MCP servers for supply-chain risks"
 Post to r/mcp, r/cybersecurity, r/ClaudeAI, r/ChatGPTCoding, X, LinkedIn
 Pin the install one-liner: uvx mcphound scan
 Watch issues for 48h — the first false-positive report is a release-blocker patch.
Rollback if something's wrong
Broken release: yank it — uv publish --yank 0.1.0 dist/* (hides it from new installs; existing users keep working), fix, publish 0.1.1. Never reuse a version number.
