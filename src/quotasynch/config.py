"""Configuration : heures d'ancrage, modèle, message et réveil du PC."""

import tomllib
from dataclasses import dataclass
from datetime import time
from pathlib import Path

WINDOW_HOURS = 5
MIN_GAP_MINUTES = WINDOW_HOURS * 60
DAY_MINUTES = 24 * 60


class ConfigError(Exception):
    """La configuration est illisible ou incohérente."""


@dataclass(frozen=True)
class Config:
    anchors: tuple[time, ...] = (time(5, 0), time(10, 1), time(15, 2))
    model: str = "haiku"
    message: str = "ok"
    wake: bool = True


def _parse_anchor(raw: object) -> time:
    try:
        if not isinstance(raw, str):
            raise ValueError
        return time.fromisoformat(raw)
    except ValueError:
        raise ConfigError(f"heure d'ancrage invalide : {raw!r} (attendu HH:MM)") from None


def _check_gaps(anchors: tuple[time, ...]) -> None:
    minutes = sorted(a.hour * 60 + a.minute for a in anchors)
    if len(minutes) != len(set(minutes)):
        raise ConfigError("deux heures d'ancrage identiques")
    gaps = [b - a for a, b in zip(minutes, minutes[1:], strict=False)]
    gaps.append(minutes[0] + DAY_MINUTES - minutes[-1])
    if len(minutes) > 1 and min(gaps) < MIN_GAP_MINUTES:
        raise ConfigError(
            f"deux heures d'ancrage sont espacées de moins de {WINDOW_HOURS} h : "
            "les fenêtres se chevaucheraient"
        )


def load_config(path: Path) -> Config:
    """Lit la configuration ; un fichier absent donne les valeurs par défaut."""
    defaults = Config()
    if not path.exists():
        return defaults
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as erreur:
        raise ConfigError(f"configuration illisible ({path}) : {erreur}") from None
    raw_anchors = data.get("anchors")
    anchors = (
        defaults.anchors if raw_anchors is None else tuple(_parse_anchor(a) for a in raw_anchors)
    )
    if not anchors:
        raise ConfigError("au moins une heure d'ancrage est nécessaire")
    _check_gaps(anchors)
    return Config(
        anchors=anchors,
        model=str(data.get("model", defaults.model)),
        message=str(data.get("message", defaults.message)),
        wake=bool(data.get("wake", defaults.wake)),
    )
