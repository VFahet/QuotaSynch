import pytest

from quotasynch import gui
from quotasynch.cli import main
from quotasynch.interface import journal_rows, load_hours
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
    assert lignes[0].detail == "fenêtre ouverte depuis 10:01"


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
