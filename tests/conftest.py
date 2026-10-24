import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from quotasynch.system import System

NOW = datetime(2026, 10, 26, 10, 1, tzinfo=timezone(timedelta(hours=2)))


@dataclass
class FakeProcess:
    """Double du lanceur de processus : enregistre les appels, renvoie un résultat fixé."""

    returncode: int = 0
    stderr: str = ""
    raises: BaseException | None = None
    returncodes: dict[str, int] = field(default_factory=dict)
    stdout: str = ""
    calls: list[tuple[list[str], dict[str, Any]]] = field(default_factory=list)

    def __call__(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """`returncodes` fixe un code par sous-commande (`args[1]`), sinon `returncode`."""
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        code = self.returncodes.get(args[1], self.returncode)
        return subprocess.CompletedProcess(args, code, stdout=self.stdout, stderr=self.stderr)


@dataclass
class Machine:
    system: System
    process: FakeProcess
    config_file: Path
    data_dir: Path

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"

    def with_process(self, process: FakeProcess) -> System:
        return System(environ=self.system.environ, run_process=process, clock=self.system.clock)


@pytest.fixture
def machine(tmp_path: Path) -> Machine:
    process = FakeProcess()
    environ = {
        "APPDATA": str(tmp_path / "roaming"),
        "LOCALAPPDATA": str(tmp_path / "local"),
        "PATH": "",
        "ANTHROPIC_API_KEY": "sk-secret",
    }
    system = System(environ=environ, run_process=process, clock=lambda: NOW)
    return Machine(
        system=system,
        process=process,
        config_file=tmp_path / "roaming" / "QuotaSynch" / "config.toml",
        data_dir=tmp_path / "local" / "QuotaSynch",
    )
