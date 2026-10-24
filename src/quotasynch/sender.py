"""Envoi du message minimal à Claude Code, par l'abonnement."""

import shutil
import subprocess

from quotasynch.config import Config
from quotasynch.system import System

TIMEOUT_SECONDS = 50
API_KEY_VARIABLE = "ANTHROPIC_API_KEY"


class SendError(Exception):
    """Le message n'a pas pu être envoyé."""


def send_message(config: Config, system: System) -> None:
    workdir = system.data_dir()
    workdir.mkdir(parents=True, exist_ok=True)
    environ = {k: v for k, v in system.environ.items() if k != API_KEY_VARIABLE}
    executable = shutil.which("claude", path=system.environ.get("PATH")) or "claude"
    args = [
        executable,
        "-p",
        config.message,
        "--model",
        config.model,
        "--no-session-persistence",
        "--strict-mcp-config",
        "--tools",
        "",
    ]
    try:
        result = system.run(
            args,
            cwd=workdir,
            env=environ,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        raise SendError("`claude` est introuvable dans le PATH") from None
    except subprocess.TimeoutExpired:
        raise SendError(f"`claude` n'a pas répondu en {TIMEOUT_SECONDS} s") from None
    if result.returncode != 0:
        sortie = (result.stderr.strip() or result.stdout.strip()).splitlines()
        detail = sortie[-1:] or ["sans message"]
        raise SendError(f"`claude` a échoué (code {result.returncode}) : {detail[0]}")
