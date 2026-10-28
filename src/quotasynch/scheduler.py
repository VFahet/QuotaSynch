"""Tâches du Planificateur de tâches Windows : l'ancrage et le relevé du quota."""

import subprocess
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from quotasynch.config import Config
from quotasynch.system import System

TASK_NAME = "QuotaSynch"
RELEVE_TASK_NAME = "QuotaSynch-releve"
TASK_FILE = "task.xml"
RELEVE_TASK_FILE = "releve-task.xml"
TIME_LIMIT = "PT2M"
RELEVE_TIME_LIMIT = "PT1M"
RELEVE_INTERVAL = "PT15M"

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
    <StartWhenAvailable>{catch_up}</StartWhenAvailable>
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

RELEVE_TRIGGER_XML = """    <TimeTrigger>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>{interval}</Interval>
      </Repetition>
    </TimeTrigger>"""


class SchedulerError(Exception):
    """Le Planificateur de tâches a refusé l'opération."""


def _task_xml(
    triggers: str, *, wake: bool, catch_up: bool, time_limit: str, command: str, arguments: str
) -> str:
    return TASK_XML.format(
        triggers=triggers,
        wake="true" if wake else "false",
        catch_up="true" if catch_up else "false",
        time_limit=time_limit,
        command=escape(command),
        arguments=escape(arguments),
    )


def build_task_xml(config: Config, command: str, arguments: str, since: date) -> str:
    triggers = "\n".join(
        TRIGGER_XML.format(start=f"{since.isoformat()}T{anchor:%H:%M}:00")
        for anchor in config.anchors
    )
    return _task_xml(
        triggers,
        wake=config.wake,
        catch_up=True,
        time_limit=TIME_LIMIT,
        command=command,
        arguments=arguments,
    )


def build_releve_task_xml(command: str, arguments: str, since: date) -> str:
    """Le relevé ne dépend pas de la configuration : pas de réveil, pas de rattrapage."""
    trigger = RELEVE_TRIGGER_XML.format(
        start=f"{since.isoformat()}T00:00:00", interval=RELEVE_INTERVAL
    )
    return _task_xml(
        trigger,
        wake=False,
        catch_up=False,
        time_limit=RELEVE_TIME_LIMIT,
        command=command,
        arguments=arguments,
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


def _presente(system: System, nom: str) -> bool:
    return _schtasks(system, "/Query", "/TN", nom).returncode == 0


def _creer(system: System, nom: str, fichier: str, xml: str) -> None:
    task_file = system.data_dir() / fichier
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(xml, encoding="utf-16")
    result = _schtasks(system, "/Create", "/TN", nom, "/XML", str(task_file), "/F")
    if result.returncode != 0:
        raise SchedulerError(f"création de la tâche {nom} refusée : {result.stderr.strip()}")


def is_installed(system: System) -> bool:
    return _presente(system, TASK_NAME)


def install(config: Config, system: System) -> str:
    interpreter = _interpreter()
    since = system.clock().date()
    _creer(
        system,
        TASK_NAME,
        TASK_FILE,
        build_task_xml(config, interpreter, "-m quotasynch run", since),
    )
    _creer(
        system,
        RELEVE_TASK_NAME,
        RELEVE_TASK_FILE,
        build_releve_task_xml(interpreter, "-m quotasynch releve", since),
    )
    heures = ", ".join(f"{a:%H:%M}" for a in config.anchors)
    reveil = "avec réveil du PC" if config.wake else "sans réveil du PC"
    return f"tâche {TASK_NAME} installée : {heures} ({reveil})"


def uninstall(system: System) -> str:
    presentes = [nom for nom in (TASK_NAME, RELEVE_TASK_NAME) if _presente(system, nom)]
    if not presentes:
        return f"tâches {TASK_NAME} et {RELEVE_TASK_NAME} déjà absentes"
    for nom in presentes:
        result = _schtasks(system, "/Delete", "/TN", nom, "/F")
        if result.returncode != 0:
            raise SchedulerError(f"suppression de la tâche {nom} refusée : {result.stderr.strip()}")
    for fichier in (TASK_FILE, RELEVE_TASK_FILE):
        (system.data_dir() / fichier).unlink(missing_ok=True)
    return f"tâches supprimées : {', '.join(presentes)}"
