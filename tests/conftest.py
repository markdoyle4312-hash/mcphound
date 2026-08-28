from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_path(rule_id: str, name: str) -> Path:
    return FIXTURES / "static" / rule_id / name
