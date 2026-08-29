.PHONY: install test lint format scan-self fixtures

install:
	uv sync --extra dev

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff format .

# Dogfood: scan this repo's own agent MCP configs
scan-self:
	uv run mcphound scan .mcp.json opencode.jsonc --fail-on high || \
		bash scripts/self-scan.sh

fixtures:
	@echo "Fixtures must contain MCPHOUND-FIXTURE-CANARY and must never be"
	@echo "referenced from .mcp.json / opencode.jsonc / any agent config."
