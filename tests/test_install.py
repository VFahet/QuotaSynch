import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from quotasynch.cli import main
from tests.conftest import FakeProcess, Machine

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def tache_installee(machine: Machine) -> ET.Element:
    [(args, _)] = machine.process.calls
    assert args[:6] == ["schtasks", "/Create", "/TN", "QuotaSynch", "/XML", args[5]]
    assert args[6] == "/F"
    return ET.fromstring(Path(args[5]).read_text(encoding="utf-16"))


def test_install_cree_une_tache_avec_un_declencheur_par_heure_d_ancrage(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["install"], machine.system)

    assert code == 0
    tache = tache_installee(machine)
    departs = [e.text for e in tache.findall(".//t:CalendarTrigger/t:StartBoundary", NS)]
    assert [d.split("T")[1] for d in departs if d] == ["05:00:00", "10:01:00", "15:02:00"]
    jours = tache.findall(".//t:ScheduleByDay/t:DaysInterval", NS)
    assert [j.text for j in jours] == ["1", "1", "1"]
    assert "installée" in capsys.readouterr().out


def test_install_active_le_rattrapage_et_tourne_sur_batterie(machine: Machine) -> None:
    main(["install"], machine.system)

    reglages = tache_installee(machine).find("t:Settings", NS)
    assert reglages is not None
    valeur = {e.tag.split("}")[1]: e.text for e in reglages}
    assert valeur["StartWhenAvailable"] == "true"
    assert valeur["DisallowStartIfOnBatteries"] == "false"
    assert valeur["StopIfGoingOnBatteries"] == "false"


def test_install_demande_le_reveil_du_pc_par_defaut(machine: Machine) -> None:
    main(["install"], machine.system)
    reveil = tache_installee(machine).find("t:Settings/t:WakeToRun", NS)
    assert reveil is not None and reveil.text == "true"


def test_install_sans_reveil_quand_la_configuration_le_desactive(machine: Machine) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text("wake = false\n", encoding="utf-8")

    main(["install"], machine.system)

    reveil = tache_installee(machine).find("t:Settings/t:WakeToRun", NS)
    assert reveil is not None and reveil.text == "false"


def test_install_lance_run_sous_le_compte_de_l_utilisateur(machine: Machine) -> None:
    main(["install"], machine.system)

    tache = tache_installee(machine)
    arguments = tache.find(".//t:Exec/t:Arguments", NS)
    assert arguments is not None and arguments.text == "-m quotasynch run"
    session = tache.find(".//t:Principal/t:LogonType", NS)
    assert session is not None and session.text == "InteractiveToken"


def test_install_refuse_une_configuration_invalide_sans_toucher_au_planificateur(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")

    assert main(["install"], machine.system) == 1
    assert machine.process.calls == []
    assert "5 h" in capsys.readouterr().err


def test_install_signale_le_refus_du_planificateur(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    refus = FakeProcess(returncode=1, stderr="Accès refusé")

    assert main(["install"], machine.with_process(refus)) == 1
    assert "Accès refusé" in capsys.readouterr().err


def test_uninstall_supprime_la_tache(machine: Machine, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["uninstall"], machine.system)

    assert code == 0
    commandes = [args[1] for args, _ in machine.process.calls]
    assert commandes == ["/Query", "/Delete"]
    assert "supprimée" in capsys.readouterr().out


def test_uninstall_sans_tache_installee_ne_fait_rien(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    absente = FakeProcess(returncodes={"/Query": 1})

    code = main(["uninstall"], machine.with_process(absente))

    assert code == 0
    assert [args[1] for args, _ in absente.calls] == ["/Query"]
    assert "absente" in capsys.readouterr().out
