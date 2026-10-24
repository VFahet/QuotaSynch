"""État de l'installation : tâche, configuration et dernier envoi."""

from datetime import timedelta

from quotasynch.anchoring import WINDOW
from quotasynch.config import Config
from quotasynch.scheduler import TASK_NAME, is_installed
from quotasynch.state import read_last_send
from quotasynch.system import System


def describe(config: Config, system: System) -> str:
    now = system.clock()
    last = read_last_send(system.state_file())
    if last is None:
        envoi = "aucun"
    elif timedelta(0) <= now - last < WINDOW:
        envoi = f"{last:%d/%m %H:%M} (fenêtre ouverte jusqu'à {last + WINDOW:%H:%M})"
    else:
        envoi = f"{last:%d/%m %H:%M} (aucune fenêtre ouverte)"
    lignes = [
        f"tâche {TASK_NAME} : {'installée' if is_installed(system) else 'non installée'}",
        f"heures d'ancrage : {', '.join(f'{a:%H:%M}' for a in config.anchors)}",
        f"réveil du PC : {'oui' if config.wake else 'non'}",
        f"dernier envoi : {envoi}",
    ]
    return "\n".join(lignes)
