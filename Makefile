.PHONY: install test lint format scan-self fixtures docs docs-check db-up db-migrate registry-poll registry-scan

install:
	uv sync --extra dev

test:
	uv run pytest -q

lint:
	uv run ruff check .

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

# Local Postgres for the registry poller (docker compose)
db-up:
	docker compose up -d db

db-migrate:
	uv run alembic upgrade head

registry-poll:
	uv run mcphound registry-poll --config config/registry.yaml

registry-scan:
	uv run mcphound registry-scan --config config/registry.yaml
