"""Fichiers JSONL en ajout seul : une ligne JSON par enregistrement."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def append(path: Path, line: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")


def read[T](path: Path, parse: Callable[[str], T], limit: int | None = None) -> list[T]:
    """Les derniers enregistrements (tous sans `limit`), le plus récent d'abord ; une ligne
    illisible est ignorée."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    found: list[T] = []
    for raw in reversed(lines):
        try:
            found.append(parse(raw))
        except (ValueError, KeyError, TypeError):
            continue
        if limit is not None and len(found) == limit:
            break
    return found
