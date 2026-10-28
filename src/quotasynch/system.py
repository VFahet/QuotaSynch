"""Frontières du système : horloge, processus, environnement et emplacements des fichiers."""

import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

APP_DIR = "QuotaSynch"

RunProcess = Callable[..., "subprocess.CompletedProcess[str]"]


def _now() -> datetime:
    return datetime.now().astimezone()


def _environ() -> Mapping[str, str]:
    return dict(os.environ)


@dataclass(frozen=True)
class System:
    environ: Mapping[str, str] = field(default_factory=_environ)
    run_process: RunProcess = subprocess.run
    clock: Callable[[], datetime] = _now

    def config_file(self) -> Path:
        base = self.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR / "config.toml"

    def data_dir(self) -> Path:
        base = self.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR

    def state_file(self) -> Path:
        return self.data_dir() / "state.json"

    def journal_file(self) -> Path:
        return self.data_dir() / "journal.jsonl"

    def snapshot_file(self) -> Path:
        return self.data_dir() / "snapshot.json"

    def releves_file(self) -> Path:
        return self.data_dir() / "releves.jsonl"

    def run(self, args: list[str], **kwargs: Any) -> "subprocess.CompletedProcess[str]":
        return self.run_process(args, **kwargs)
