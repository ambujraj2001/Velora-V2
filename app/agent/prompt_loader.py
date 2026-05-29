from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _read_prompt_file(name: str) -> str:
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8").strip()


def load_query_format_hint(db_type: str) -> str:
    if db_type == "postgres":
        return _read_prompt_file("postgres_hint.txt")
    return _read_prompt_file("mongodb_hint.txt")


def load_system_prompt(*, tenant_name: str, db_type: str, query_format_hint: str) -> str:
    template = _read_prompt_file("system.txt")
    return template.format(
        tenant_name=tenant_name,
        db_type=db_type,
        query_format_hint=query_format_hint,
    )
