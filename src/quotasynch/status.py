"""État de l'installation : tâche, configuration et dernier envoi."""

from quotasynch import journal
from quotasynch.anchoring import WINDOW, window_open
from quotasynch.config import Config
from quotasynch.scheduler import TASK_NAME, is_installed
from quotasynch.state import read_last_send
from quotasynch.system import System


def _last_anchor(system: System) -> str:
    entries = journal.read(system.journal_file(), limit=1)
    if not entries:
        return "aucun"
    entry = entries[0]
    prevu = "inconnu" if entry.planned is None else f"{entry.planned:%H:%M}"
    ligne = f"{entry.label}, prévu {prevu}, parti {entry.actual:%H:%M}"
    if entry.delay_minutes is not None:
        ligne += f" (retard {entry.delay_minutes} min)"
    return f"{ligne} : {entry.detail}" if entry.detail and entry.result != journal.SENT else ligne


def describe(config: Config, system: System) -> str:
    now = system.clock()
    last = read_last_send(system.state_file())
    if last is None:
        envoi = "aucun"
    elif window_open(now, last):
        envoi = f"{last:%d/%m %H:%M} (fenêtre ouverte jusqu'à {last + WINDOW:%H:%M})"
    else:
        envoi = f"{last:%d/%m %H:%M} (aucune fenêtre ouverte)"
    lignes = [
        f"tâche {TASK_NAME} : {'installée' if is_installed(system) else 'non installée'}",
        f"heures d'ancrage : {', '.join(f'{a:%H:%M}' for a in config.anchors)}",
        f"réveil du PC : {'oui' if config.wake else 'non'}",
        f"dernier envoi : {envoi}",
        f"dernier ancrage : {_last_anchor(system)}",
    ]
    return "\n".join(lignes)
