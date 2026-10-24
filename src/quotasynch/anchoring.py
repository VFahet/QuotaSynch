"""Un ancrage : envoyer le message, sauf si une fenêtre est déjà ouverte."""

from datetime import datetime, timedelta

from quotasynch.config import WINDOW_HOURS, Config
from quotasynch.sender import send_message
from quotasynch.state import read_last_send, write_last_send
from quotasynch.system import System

WINDOW = timedelta(hours=WINDOW_HOURS)


def window_open(now: datetime, last_send: datetime | None) -> bool:
    """Vrai si le dernier envoi date de moins de 5 h (une horloge reculée ne compte pas)."""
    return last_send is not None and timedelta(0) <= now - last_send < WINDOW


def run_anchor(config: Config, system: System) -> str:
    """Exécute un ancrage et renvoie une phrase qui dit ce qui s'est passé."""
    now = system.clock()
    last = read_last_send(system.state_file())
    if last is not None and window_open(now, last):
        return f"saut : une fenêtre est ouverte depuis {last:%d/%m %H:%M}"
    send_message(config, system)
    write_last_send(system.state_file(), now)
    return f"envoyé à {now:%d/%m %H:%M}"
