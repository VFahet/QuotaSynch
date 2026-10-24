import subprocess
from datetime import datetime, timedelta

import pytest

from quotasynch.cli import main
from quotasynch.state import write_last_send
from quotasynch.system import System
from tests.conftest import NOW, FakeProcess, Machine


def _at(hour: int, minute: int, day: int = 26) -> datetime:
    return NOW.replace(day=day, hour=hour, minute=minute)


def _machine_at(machine: Machine, moment: datetime) -> Machine:
    machine.system = System(
        environ=machine.system.environ, run_process=machine.process, clock=lambda: moment
    )
    return machine


def test_un_envoi_laisse_une_ligne_avec_l_heure_prevue_et_l_heure_reelle(
    machine: Machine,
) -> None:
    moment = _at(10, 3)

    main(["run"], _machine_at(machine, moment).system)

    assert machine.journal() == [
        {
            "prevue": "2026-10-26T10:01:00+02:00",
            "reelle": "2026-10-26T10:03:00+02:00",
            "resultat": "envoye",
            "detail": None,
        }
    ]


@pytest.mark.parametrize(
    ("moment", "prevue"),
    [
        (_at(3, 0), "2026-10-25T15:02:00+02:00"),
        (_at(5, 0), "2026-10-26T05:00:00+02:00"),
        (_at(9, 59), "2026-10-26T05:00:00+02:00"),
        (_at(23, 30), "2026-10-26T15:02:00+02:00"),
    ],
    ids=["avant-la-premiere-veille", "pile-a-l-heure", "entre-deux", "apres-la-derniere"],
)
def test_l_heure_prevue_est_la_derniere_heure_d_ancrage_passee(
    machine: Machine, moment: datetime, prevue: str
) -> None:
    main(["run"], _machine_at(machine, moment).system)

    assert machine.journal()[0]["prevue"] == prevue


def test_un_saut_est_consigne_avec_le_depuis_quand_de_la_fenetre(machine: Machine) -> None:
    write_last_send(machine.state_file, NOW - timedelta(hours=2))

    main(["run"], machine.system)

    [ligne] = machine.journal()
    assert ligne["resultat"] == "saut"
    assert ligne["reelle"] == NOW.isoformat()
    assert ligne["detail"] == "fenêtre ouverte depuis 08:01"


def test_un_echec_est_consigne_avec_la_derniere_ligne_d_erreur_de_claude(
    machine: Machine,
) -> None:
    process = FakeProcess(returncode=1, stderr="warning\nnot logged in")

    main(["run"], machine.with_process(process))

    [ligne] = machine.journal()
    assert ligne["resultat"] == "echec"
    assert "not logged in" in ligne["detail"]


def test_les_ancrages_s_ajoutent_au_journal_sans_l_ecraser(machine: Machine) -> None:
    main(["run"], _machine_at(machine, _at(5, 0)).system)
    main(["run"], _machine_at(machine, _at(10, 1)).system)

    assert [ligne["resultat"] for ligne in machine.journal()] == ["envoye", "envoye"]


def test_un_journal_impossible_a_ecrire_n_altere_pas_le_resultat_de_l_envoi(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    machine.journal_file.mkdir(parents=True)  # un dossier à la place du fichier

    code = main(["run"], machine.system)

    assert code == 0
    assert len(machine.process.calls) == 1
    assert "journal" in capsys.readouterr().err


def test_un_echec_d_envoi_reste_un_echec_meme_si_le_journal_est_illisible(
    machine: Machine,
) -> None:
    machine.journal_file.mkdir(parents=True)
    process = FakeProcess(raises=subprocess.TimeoutExpired("claude", 50))

    assert main(["run"], machine.with_process(process)) == 1
