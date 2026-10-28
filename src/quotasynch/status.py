"""État de l'installation : tâche, configuration et dernier envoi."""

import math

from quotasynch import journal
from quotasynch.anchoring import WINDOW, window_open
from quotasynch.config import Config
from quotasynch.releves import Limite, read_last
from quotasynch.scheduler import RELEVE_TASK_NAME, TASK_NAME, is_installed, is_releve_installed
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


def _pourcentage(limite: Limite | None) -> str:
    if limite is None:
        return "–"
    return f"{math.floor(limite.pct + 0.5)} %"


def _dernier_releve(system: System) -> str:
    releve = read_last(system.releves_file())
    if releve is None:
        return "aucun"
    minutes = int((system.clock() - releve.heure).total_seconds() // 60)
    fenetre = _pourcentage(releve.fenetre)
    semaine = _pourcentage(releve.semaine)
    return f"fenêtre {fenetre}, semaine {semaine} (il y a {minutes} min)"


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
        f"tâche {RELEVE_TASK_NAME} : "
        f"{'installée' if is_releve_installed(system) else 'non installée'}",
        f"heures d'ancrage : {', '.join(f'{a:%H:%M}' for a in config.anchors)}",
        f"réveil du PC : {'oui' if config.wake else 'non'}",
        f"dernier envoi : {envoi}",
        f"dernier ancrage : {_last_anchor(system)}",
        f"dernier relevé : {_dernier_releve(system)}",
    ]
    return "\n".join(lignes)
