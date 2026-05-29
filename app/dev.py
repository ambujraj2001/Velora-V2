import os
import tomllib
from pathlib import Path

import uvicorn

# Ensure request/tool logs appear in the terminal immediately during long agent runs.
os.environ.setdefault("PYTHONUNBUFFERED", "1")

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _load_config() -> dict:
    with _PYPROJECT.open("rb") as f:
        return tomllib.load(f).get("tool", {}).get("uvicorn", {})


def main() -> None:
    cfg = _load_config()
    uvicorn.run(
        cfg.get("app", "app.main:app"),
        host=cfg.get("host", "127.0.0.1"),
        port=cfg.get("port", 8000),
        reload=cfg.get("reload", True),
        reload_includes=cfg.get("reload-include", ["*.py"]),
        log_config=None,
        access_log=True,
    )


if __name__ == "__main__":
    main()
