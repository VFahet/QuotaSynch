"""Point d'entrée de la commande `quotasynch`."""

import argparse
import sys
from collections.abc import Sequence

from quotasynch.anchoring import run_anchor
from quotasynch.config import ConfigError, load_config
from quotasynch.sender import SendError
from quotasynch.system import System


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quotasynch", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="exécute un ancrage (ce que lance la tâche planifiée)")
    return parser


def main(argv: Sequence[str] | None = None, system: System | None = None) -> int:
    args = build_parser().parse_args(argv)
    system = system or System()
    try:
        config = load_config(system.config_file())
        if args.command == "run":
            print(run_anchor(config, system))
    except (ConfigError, SendError) as erreur:
        print(f"quotasynch : {erreur}", file=sys.stderr)
        return 1
    return 0
