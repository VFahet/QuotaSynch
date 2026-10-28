import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from quotasynch.cli import main
from tests.conftest import FakeProcess, Machine

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
ANCRAGE = "QuotaSynch"
RELEVE = "QuotaSynch-releve"


@dataclass
class PlanificateurFictif(FakeProcess):
    """Double du Planificateur : `presentes` existent, `refusees` refusent tout sauf la requête."""

    presentes: frozenset[str] = frozenset()
    refusees: frozenset[str] = frozenset()

    def __call__(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nom = args[3]
        if args[1] == "/Query":
            self.calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0 if nom in self.presentes else 1)
        if nom in self.refusees:
            self.calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 1, stderr="Accès refusé")
        return super().__call__(args, **kwargs)


def tache_installee(machine: Machine, nom: str = ANCRAGE) -> ET.Element:
    [args] = [args for args, _ in machine.process.calls if args[1:4] == ["/Create", "/TN", nom]]
    assert args[:6] == ["schtasks", "/Create", "/TN", nom, "/XML", args[5]]
    assert args[6] == "/F"
    return ET.fromstring(Path(args[5]).read_text(encoding="utf-16"))


def test_install_pose_aussi_la_tache_de_releve(machine: Machine) -> None:
    main(["install"], machine.system)

    creations = [args[3] for args, _ in machine.process.calls if args[1] == "/Create"]
    assert creations == [ANCRAGE, RELEVE]


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


def test_uninstall_sans_tache_installee_ne_fait_rien(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    absente = FakeProcess(returncodes={"/Query": 1})

    code = main(["uninstall"], machine.with_process(absente))

    assert code == 0
    assert [args[1] for args, _ in absente.calls] == ["/Query", "/Query"]
    assert "absente" in capsys.readouterr().out


def test_releve_repete_toutes_les_15_min_sans_fin(machine: Machine) -> None:
    main(["install"], machine.system)

    declencheur = tache_installee(machine, RELEVE).find("t:Triggers/t:TimeTrigger", NS)
    assert declencheur is not None
    intervalle = declencheur.find("t:Repetition/t:Interval", NS)
    assert intervalle is not None and intervalle.text == "PT15M"
    assert declencheur.find("t:Repetition/t:Duration", NS) is None


def test_releve_ne_reveille_pas_le_pc_ni_ne_rattrape_meme_avec_le_reveil_active(
    machine: Machine,
) -> None:
    main(["install"], machine.system)

    reglages = tache_installee(machine, RELEVE).find("t:Settings", NS)
    assert reglages is not None
    valeur = {e.tag.split("}")[1]: e.text for e in reglages}
    assert valeur["WakeToRun"] == "false"
    assert valeur["StartWhenAvailable"] == "false"


def test_releve_limite_l_execution_a_une_minute(machine: Machine) -> None:
    main(["install"], machine.system)

    reglages = tache_installee(machine, RELEVE).find("t:Settings", NS)
    assert reglages is not None
    valeur = {e.tag.split("}")[1]: e.text for e in reglages}
    assert valeur["ExecutionTimeLimit"] == "PT1M"


def test_releve_lance_la_commande_releve(machine: Machine) -> None:
    main(["install"], machine.system)

    tache = tache_installee(machine, RELEVE)
    arguments = tache.find(".//t:Exec/t:Arguments", NS)
    assert arguments is not None and arguments.text == "-m quotasynch releve"


def test_uninstall_supprime_les_deux_taches(machine: Machine) -> None:
    main(["uninstall"], machine.system)

    suppressions = [args[3] for args, _ in machine.process.calls if args[1] == "/Delete"]
    assert suppressions == [ANCRAGE, RELEVE]


def test_uninstall_retire_les_deux_fichiers_xml(machine: Machine) -> None:
    main(["install"], machine.system)
    assert (machine.data_dir / "task.xml").exists()
    assert (machine.data_dir / "releve-task.xml").exists()

    main(["uninstall"], machine.system)

    assert not (machine.data_dir / "task.xml").exists()
    assert not (machine.data_dir / "releve-task.xml").exists()


def test_uninstall_ne_signale_absente_que_si_aucune_tache_n_existe(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    seule_la_releve = PlanificateurFictif(presentes=frozenset({RELEVE}))

    assert main(["uninstall"], machine.with_process(seule_la_releve)) == 0

    suppressions = [args[3] for args, _ in seule_la_releve.calls if args[1] == "/Delete"]
    assert suppressions == [RELEVE]
    assert "supprimée" in capsys.readouterr().out


def test_uninstall_signale_le_refus_de_suppression_de_la_releve(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    refus = PlanificateurFictif(
        presentes=frozenset({ANCRAGE, RELEVE}), refusees=frozenset({RELEVE})
    )

    assert main(["uninstall"], machine.with_process(refus)) == 1
    assert "Accès refusé" in capsys.readouterr().err


def test_install_signale_le_refus_de_la_tache_de_releve(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    refus = PlanificateurFictif(refusees=frozenset({RELEVE}))

    assert main(["install"], machine.with_process(refus)) == 1
    erreur = capsys.readouterr().err
    assert "Accès refusé" in erreur
    assert f"tâche {ANCRAGE} installée" in erreur
