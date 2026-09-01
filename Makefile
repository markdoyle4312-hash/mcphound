.PHONY: install test lint typecheck format scan-self fixtures docs docs-check rules-check db-up db-migrate registry-poll registry-scan

install:
	uv sync --extra dev

test:
	uv run pytest -q

lint:
	uv run ruff check .

# Extras included so sqlalchemy/fastapi-backed modules (registry/, api/) type-check too.
typecheck:
	uv run --extra dev --extra registry --extra api mypy src/mcphound

format:
	uv run ruff format .

# Dogfood: scan this repo's own agent MCP configs (project-local only, not the machine's)
scan-self:
	uv run mcphound scan --self --fail-on high

fixtures:
	@echo "Fixtures must contain MCPHOUND-FIXTURE-CANARY and must never be"
	@echo "referenced from .mcp.json / opencode.jsonc / any agent config."

# Regenerate docs/rules.md from src/mcphound/rules/*.yaml
docs:
	uv run python scripts/generate_rule_docs.py

# CI guard: fail if docs/rules.md is stale relative to the rule YAML files
docs-check: docs
	git diff --exit-code docs/rules.md

# CI guard: fail if any rule is missing a malicious/benign fixture or a test
rules-check:
	uv run python scripts/check_rule_artifacts.py

# Local Postgres for the registry poller (docker compose)
db-up:
	docker compose up -d db

db-migrate:
	uv run alembic upgrade head

registry-poll:
	uv run mcphound registry-poll --config config/registry.yaml

registry-scan:
	uv run mcphound registry-scan --config config/registry.yaml
