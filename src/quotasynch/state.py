"""État minimal : la date du dernier envoi réussi."""

import json
from datetime import datetime
from pathlib import Path


def read_last_send(path: Path) -> datetime | None:
    """Date du dernier envoi, ou None si le fichier est absent ou illisible."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))["last_send"]
        moment = datetime.fromisoformat(raw)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return moment if moment.tzinfo is not None else None


def write_last_send(path: Path, moment: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_send": moment.isoformat()}), encoding="utf-8")
