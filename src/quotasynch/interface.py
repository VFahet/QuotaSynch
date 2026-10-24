"""La logique de l'interface, sans `tkinter` : ce que la couche d'affichage montre."""

from dataclasses import dataclass, replace

from quotasynch import journal, scheduler
from quotasynch.config import Config, ConfigError, load_config, parse_anchors, write_config
from quotasynch.system import System

JOURNAL_LIMIT = 50
NONE = "—"


@dataclass(frozen=True)
class JournalRow:
    planned: str
    actual: str
    delay: str
    result: str
    detail: str


@dataclass(frozen=True)
class HoursView:
    hours: list[str]
    problem: str | None = None


def journal_rows(system: System, limit: int = JOURNAL_LIMIT) -> list[JournalRow]:
    """Les derniers ancrages, le plus récent d'abord, déjà mis en forme."""
    rows = []
    for entry in journal.read(system.journal_file(), limit=limit):
        rows.append(
            JournalRow(
                planned=NONE if entry.planned is None else f"{entry.planned:%d/%m %H:%M}",
                actual=f"{entry.actual:%d/%m %H:%M}",
                delay=NONE if entry.delay_minutes is None else f"{entry.delay_minutes} min",
                result=entry.label,
                detail=entry.detail or "",
            )
        )
    return rows


def load_hours(system: System) -> HoursView:
    """Les heures d'ancrage à montrer ; une configuration invalide ouvre les valeurs par défaut."""
    try:
        config = load_config(system.config_file())
    except ConfigError as erreur:
        return HoursView([f"{a:%H:%M}" for a in Config().anchors], str(erreur))
    return HoursView([f"{a:%H:%M}" for a in config.anchors])


def save_hours(system: System, texts: list[str]) -> str:
    """Valide les heures, réécrit la configuration et recrée la tâche planifiée.

    Lève `ConfigError` avant toute écriture si les heures sont invalides, et
    `SchedulerError` si le Planificateur refuse (la configuration reste alors écrite).
    """
    anchors = tuple(sorted(parse_anchors([text.strip() for text in texts])))
    try:
        current = load_config(system.config_file())
    except ConfigError:
        current = Config()  # un fichier invalide est remplacé par les heures saisies
    config = replace(current, anchors=anchors)
    write_config(system.config_file(), config)
    return scheduler.install(config, system)
