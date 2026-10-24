"""Le journal : une ligne JSON par ancrage, en ajout seul."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SENT = "envoye"
SKIPPED = "saut"
FAILED = "echec"

LABELS = {SENT: "envoyé", SKIPPED: "saut", FAILED: "échec"}


@dataclass(frozen=True)
class Entry:
    planned: datetime | None
    actual: datetime
    result: str
    detail: str | None = None

    @property
    def delay(self) -> timedelta | None:
        """Le retard : l'écart entre l'heure réelle et l'heure prévue."""
        return None if self.planned is None else self.actual - self.planned

    @property
    def delay_minutes(self) -> int | None:
        return None if self.delay is None else int(self.delay.total_seconds() // 60)

    @property
    def label(self) -> str:
        return LABELS.get(self.result, self.result)


def append(path: Path, entry: Entry) -> None:
    line = {
        "prevue": entry.planned.isoformat() if entry.planned else None,
        "reelle": entry.actual.isoformat(),
        "resultat": entry.result,
        "detail": entry.detail,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")


def _parse(raw: str) -> Entry:
    data = json.loads(raw)
    planned = data["prevue"]
    detail = data["detail"]
    return Entry(
        planned=None if planned is None else datetime.fromisoformat(planned),
        actual=datetime.fromisoformat(data["reelle"]),
        result=str(data["resultat"]),
        detail=None if detail is None else str(detail),
    )


def read(path: Path, limit: int | None = None) -> list[Entry]:
    """Les derniers ancrages, le plus récent d'abord ; une ligne illisible est ignorée."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[Entry] = []
    for raw in reversed(lines):
        try:
            entries.append(_parse(raw))
        except (ValueError, KeyError, TypeError):
            continue
        if limit is not None and len(entries) == limit:
            break
    return entries
