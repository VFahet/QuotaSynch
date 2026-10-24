"""Tâche du Planificateur de tâches Windows : un déclencheur quotidien par heure d'ancrage."""

import subprocess
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from quotasynch.config import Config
from quotasynch.system import System

TASK_NAME = "QuotaSynch"
TIME_LIMIT = "PT2M"

TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
{triggers}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>{wake}</WakeToRun>
    <ExecutionTimeLimit>{time_limit}</ExecutionTimeLimit>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""

TRIGGER_XML = """    <CalendarTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>"""


class SchedulerError(Exception):
    """Le Planificateur de tâches a refusé l'opération."""


def build_task_xml(config: Config, command: str, arguments: str, since: date) -> str:
    triggers = "\n".join(
        TRIGGER_XML.format(start=f"{since.isoformat()}T{anchor:%H:%M}:00")
        for anchor in config.anchors
    )
    return TASK_XML.format(
        triggers=triggers,
        wake="true" if config.wake else "false",
        time_limit=TIME_LIMIT,
        command=escape(command),
        arguments=escape(arguments),
    )


def _interpreter() -> str:
    """Le Python courant, sans fenêtre de console si `pythonw.exe` est à côté."""
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")
    return str(windowless if windowless.exists() else python)


def _schtasks(system: System, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return system.run(
            ["schtasks", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as erreur:
        raise SchedulerError(f"`schtasks` est inutilisable : {erreur}") from None


def is_installed(system: System) -> bool:
    return _schtasks(system, "/Query", "/TN", TASK_NAME).returncode == 0


def install(config: Config, system: System) -> str:
    xml = build_task_xml(config, _interpreter(), "-m quotasynch run", system.clock().date())
    task_file = system.data_dir() / "task.xml"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(xml, encoding="utf-16")
    result = _schtasks(system, "/Create", "/TN", TASK_NAME, "/XML", str(task_file), "/F")
    if result.returncode != 0:
        raise SchedulerError(f"création de la tâche refusée : {result.stderr.strip()}")
    heures = ", ".join(f"{a:%H:%M}" for a in config.anchors)
    reveil = "avec réveil du PC" if config.wake else "sans réveil du PC"
    return f"tâche {TASK_NAME} installée : {heures} ({reveil})"


def uninstall(system: System) -> str:
    if not is_installed(system):
        return f"tâche {TASK_NAME} déjà absente"
    result = _schtasks(system, "/Delete", "/TN", TASK_NAME, "/F")
    if result.returncode != 0:
        raise SchedulerError(f"suppression de la tâche refusée : {result.stderr.strip()}")
    return f"tâche {TASK_NAME} supprimée"
