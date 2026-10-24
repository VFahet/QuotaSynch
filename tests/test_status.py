from datetime import timedelta

import pytest

from quotasynch.cli import main
from quotasynch.state import write_last_send
from tests.conftest import NOW, FakeProcess, Machine


def test_status_dit_que_la_tache_est_installee_et_montre_la_configuration(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["status"], machine.system)

    sortie = capsys.readouterr().out
    assert code == 0
    assert "installée" in sortie and "non installée" not in sortie
    assert "05:00, 10:01, 15:02" in sortie
    assert "réveil du PC : oui" in sortie
    assert "dernier envoi : aucun" in sortie


def test_status_signale_une_tache_non_installee(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    absente = FakeProcess(returncode=1)

    assert main(["status"], machine.with_process(absente)) == 0
    assert "non installée" in capsys.readouterr().out


def test_status_donne_la_fin_de_la_fenetre_ouverte(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    write_last_send(machine.state_file, NOW - timedelta(hours=1))

    main(["status"], machine.system)

    assert "fenêtre ouverte jusqu'à 14:01" in capsys.readouterr().out


def test_status_apres_la_fin_de_la_fenetre(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    write_last_send(machine.state_file, NOW - timedelta(hours=6))

    main(["status"], machine.system)

    assert "aucune fenêtre ouverte" in capsys.readouterr().out


def test_status_dit_qu_aucun_ancrage_n_est_consigne(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["status"], machine.system)

    assert "dernier ancrage : aucun" in capsys.readouterr().out


def test_status_montre_le_dernier_ancrage_avec_son_retard(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["run"], machine.system)  # NOW = 10:01, heure prévue 10:01
    capsys.readouterr()

    main(["status"], machine.system)

    assert "dernier ancrage : envoyé, prévu 10:01, parti 10:01 (retard 0 min)" in (
        capsys.readouterr().out
    )


def test_status_montre_un_echec_avec_son_detail_et_sans_heure_prevue(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")
    main(["run"], machine.system)
    machine.config_file.write_text('anchors = ["05:00"]\n', encoding="utf-8")
    capsys.readouterr()

    main(["status"], machine.system)

    ligne = next(x for x in capsys.readouterr().out.splitlines() if "dernier ancrage" in x)
    assert ligne.startswith("dernier ancrage : échec, prévu inconnu, parti 10:01 : ")
    assert "5 h" in ligne
