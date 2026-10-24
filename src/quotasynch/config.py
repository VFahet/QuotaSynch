"""Configuration : heures d'ancrage, modèle, message et réveil du PC."""

import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, time
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
        return datetime.strptime(raw, "%H:%M").time()
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


def parse_anchors(raw: object) -> tuple[time, ...]:
    """Valide une liste d'heures `HH:MM` : non vide, sans doublon, espacées d'au moins 5 h."""
    if not isinstance(raw, list):
        raise ConfigError('`anchors` doit être une liste, par exemple ["05:00", "10:01"]')
    anchors = tuple(_parse_anchor(a) for a in raw)
    if not anchors:
        raise ConfigError("au moins une heure d'ancrage est nécessaire")
    _check_gaps(anchors)
    return anchors


def _typed[T](data: dict[str, object], key: str, kind: type[T], default: T) -> T:
    value = data.get(key, default)
    if not isinstance(value, kind):
        raise ConfigError(f"`{key}` doit être de type {kind.__name__}")
    return value


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
    anchors = defaults.anchors if raw_anchors is None else parse_anchors(raw_anchors)
    return Config(
        anchors=anchors,
        model=_typed(data, "model", str, defaults.model),
        message=_typed(data, "message", str, defaults.message),
        wake=_typed(data, "wake", bool, defaults.wake),
    )


def write_config(path: Path, config: Config) -> None:
    """Réécrit la configuration ; les commentaires d'un fichier édité à la main sont perdus."""
    anchors = ", ".join(json.dumps(f"{a:%H:%M}") for a in config.anchors)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"anchors = [{anchors}]\n"
        f"model = {json.dumps(config.model, ensure_ascii=False)}\n"
        f"message = {json.dumps(config.message, ensure_ascii=False)}\n"
        f"wake = {'true' if config.wake else 'false'}\n",
        encoding="utf-8",
    )
