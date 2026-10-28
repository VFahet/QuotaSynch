"""Point d'entrée de la commande `quotasynch`."""

import argparse
import sys
from collections.abc import Sequence

from quotasynch import releves, scheduler
from quotasynch.anchoring import record_config_failure, run_anchor
from quotasynch.config import ConfigError, load_config
from quotasynch.scheduler import SchedulerError
from quotasynch.sender import SendError
from quotasynch.status import describe
from quotasynch.system import System


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quotasynch", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="exécute un ancrage (ce que lance la tâche planifiée)")
    commands.add_parser("install", help="crée la tâche du Planificateur de tâches")
    commands.add_parser("uninstall", help="supprime la tâche du Planificateur de tâches")
    commands.add_parser("gui", help="ouvre l'interface : heures d'ancrage et journal")
    commands.add_parser("status", help="montre la tâche, la configuration et le dernier envoi")
    commands.add_parser("releve", help="ajoute un relevé du quota depuis l'instantané")
    return parser


def main(argv: Sequence[str] | None = None, system: System | None = None) -> int:
    args = build_parser().parse_args(argv)
    system = system or System()
    try:
        if args.command == "gui":
            from quotasynch import gui  # tkinter ne se charge que pour l'interface

            gui.open_interface(system)
            return 0
        if args.command == "uninstall":
            print(scheduler.uninstall(system))
            return 0
        if args.command == "releve":
            releves.releve(system)
            return 0
        try:
            config = load_config(system.config_file())
        except ConfigError as erreur:
            if args.command == "run":
                record_config_failure(system, erreur)
            raise
        if args.command == "run":
            print(run_anchor(config, system))
        elif args.command == "install":
            print(scheduler.install(config, system))
        elif args.command == "status":
            print(describe(config, system))
    except (ConfigError, SendError, SchedulerError, OSError) as erreur:
        print(f"quotasynch : {erreur}", file=sys.stderr)
        return 1
    return 0
