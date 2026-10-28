from datetime import time

import pytest

from quotasynch import gui
from quotasynch.cli import main
from quotasynch.config import ConfigError, load_config
from quotasynch.interface import journal_rows, load_hours, save_hours
from quotasynch.scheduler import SchedulerError
from quotasynch.system import System
from tests.conftest import NOW, FakeProcess, Machine


def test_gui_ouvre_l_interface_meme_avec_une_configuration_invalide(
    machine: Machine, monkeypatch: pytest.MonkeyPatch
) -> None:
    ouvertes: list[System] = []
    monkeypatch.setattr(gui, "open_interface", ouvertes.append)
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")

    assert main(["gui"], machine.system) == 0
    assert ouvertes == [machine.system]


def test_le_journal_vide_donne_aucune_ligne(machine: Machine) -> None:
    assert journal_rows(machine.system) == []


def test_le_journal_se_lit_du_plus_recent_au_plus_ancien_avec_le_retard(
    machine: Machine,
) -> None:
    main(["run"], machine.system)  # envoi à 10:01, prévu 10:01
    main(["run"], machine.system)  # saut : la fenêtre vient de s'ouvrir
    main(["run"], machine.with_process(FakeProcess()))

    lignes = journal_rows(machine.system)

    assert [ligne.result for ligne in lignes] == ["saut", "saut", "envoyé"]
    assert lignes[-1].planned == "26/10 10:01"
    assert lignes[-1].actual == "26/10 10:01"
    assert lignes[-1].delay == "0 min"
    assert lignes[0].detail == "fenêtre ouverte depuis 26/10 10:01"


def test_une_ligne_sans_heure_prevue_s_affiche_avec_un_tiret(machine: Machine) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")
    main(["run"], machine.system)

    [ligne] = journal_rows(machine.system)

    assert (ligne.planned, ligne.delay, ligne.result) == ("—", "—", "échec")
    assert ligne.actual == f"{NOW:%d/%m %H:%M}"


def test_le_journal_est_limite_aux_derniers_ancrages(machine: Machine) -> None:
    for _ in range(5):
        main(["run"], machine.system)

    assert len(journal_rows(machine.system, limit=3)) == 3


def test_les_heures_de_l_interface_viennent_de_la_configuration(machine: Machine) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["06:30", "12:00"]\n', encoding="utf-8")

    vue = load_hours(machine.system)

    assert vue.hours == ["06:30", "12:00"]
    assert vue.problem is None


def test_une_configuration_invalide_ouvre_les_heures_par_defaut_et_dit_pourquoi(
    machine: Machine,
) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")

    vue = load_hours(machine.system)

    assert vue.hours == ["05:00", "10:01", "15:02"]
    assert vue.problem is not None and "5 h" in vue.problem


def _task_xml(machine: Machine) -> str:
    return (machine.data_dir / "task.xml").read_text(encoding="utf-16")


def test_enregistrer_reecrit_la_configuration_et_recree_la_tache(machine: Machine) -> None:
    message = save_hours(machine.system, ["12:00", "06:30"])

    xml = _task_xml(machine)
    assert load_config(machine.config_file).anchors == (time(6, 30), time(12, 0))
    assert "T06:30:00" in xml and "T12:00:00" in xml and "T05:00:00" not in xml
    creations = [args for args, _ in machine.process.calls if args[1] == "/Create"]
    assert [args[3] for args in creations] == ["QuotaSynch", "QuotaSynch-releve"]
    assert all(
        args[:3] == ["schtasks", "/Create", "/TN"] and args[-1] == "/F" for args in creations
    )
    assert "06:30, 12:00" in message


def test_enregistrer_garde_le_modele_le_message_et_le_reveil(machine: Machine) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text(
        'anchors = ["05:00"]\nmodel = "sonnet"\nmessage = "dis \\"ok\\""\nwake = false\n',
        encoding="utf-8",
    )

    save_hours(machine.system, ["07:00"])

    config = load_config(machine.config_file)
    assert (config.model, config.message, config.wake) == ("sonnet", 'dis "ok"', False)
    assert "<WakeToRun>false</WakeToRun>" in _task_xml(machine)


def test_enregistrer_accepte_des_espaces_autour_des_heures(machine: Machine) -> None:
    save_hours(machine.system, [" 08:00 ", "14:00"])

    assert load_config(machine.config_file).anchors == (time(8, 0), time(14, 0))


@pytest.mark.parametrize(
    ("heures", "attendu"),
    [
        (["05:00", "09:00"], "5 h"),
        (["05:00", "05:00"], "identiques"),
        (["25:00"], "invalide"),
        (["midi"], "invalide"),
        ([], "au moins une"),
    ],
    ids=["trop-proches", "doublon", "heure-impossible", "texte", "aucune"],
)
def test_enregistrer_refuse_des_heures_invalides_sans_rien_modifier(
    machine: Machine, heures: list[str], attendu: str
) -> None:
    with pytest.raises(ConfigError, match=attendu):
        save_hours(machine.system, heures)

    assert not machine.config_file.exists()
    assert machine.process.calls == []


def test_enregistrer_garde_la_configuration_quand_le_planificateur_refuse(
    machine: Machine,
) -> None:
    refus = FakeProcess(returncode=1, stderr="Accès refusé")

    with pytest.raises(SchedulerError, match="Accès refusé"):
        save_hours(machine.with_process(refus), ["07:00"])

    assert load_config(machine.config_file).anchors == (time(7, 0),)


def test_enregistrer_remplace_une_configuration_invalide_par_les_heures_saisies(
    machine: Machine,
) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")

    save_hours(machine.system, ["05:00", "11:00"])

    assert load_config(machine.config_file).anchors == (time(5, 0), time(11, 0))
