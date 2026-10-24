"""Un ancrage : envoyer le message, sauf si une fenêtre est déjà ouverte."""

import sys
from datetime import datetime, time, timedelta

from quotasynch import journal
from quotasynch.config import WINDOW_HOURS, Config
from quotasynch.sender import SendError, send_message
from quotasynch.state import read_last_send, write_last_send
from quotasynch.system import System

WINDOW = timedelta(hours=WINDOW_HOURS)


def window_open(now: datetime, last_send: datetime | None) -> bool:
    """Vrai si le dernier envoi date de moins de 5 h (une horloge reculée ne compte pas)."""
    return last_send is not None and timedelta(0) <= now - last_send < WINDOW


def planned_time(now: datetime, anchors: tuple[time, ...]) -> datetime:
    """L'heure prévue : la dernière heure d'ancrage inférieure ou égale à `now`."""
    passed = [
        moment
        for day in (now, now - timedelta(days=1))
        for anchor in anchors
        if (moment := day.replace(hour=anchor.hour, minute=anchor.minute, second=0, microsecond=0))
        <= now
    ]
    return max(passed)


def record(system: System, entry: journal.Entry) -> None:
    """Consigne l'ancrage ; si le journal est inécrivable, avertit sans changer le résultat."""
    try:
        journal.append(system.journal_file(), entry)
    except OSError as erreur:
        print(f"quotasynch : journal inécrivable ({erreur})", file=sys.stderr)


def run_anchor(config: Config, system: System) -> str:
    """Exécute un ancrage et renvoie une phrase qui dit ce qui s'est passé."""
    now = system.clock()
    planned = planned_time(now, config.anchors)
    last = read_last_send(system.state_file())
    if last is not None and window_open(now, last):
        depuis = f"fenêtre ouverte depuis {last:%H:%M}"
        record(system, journal.Entry(planned, now, journal.SKIPPED, depuis))
        return f"saut : une fenêtre est ouverte depuis {last:%d/%m %H:%M}"
    try:
        send_message(config, system)
    except SendError as erreur:
        record(system, journal.Entry(planned, now, journal.FAILED, str(erreur)))
        raise
    write_last_send(system.state_file(), now)
    record(system, journal.Entry(planned, now, journal.SENT))
    return f"envoyé à {now:%d/%m %H:%M}"
