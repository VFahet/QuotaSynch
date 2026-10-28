import dataclasses
import json
from datetime import datetime, timedelta
from typing import Any

import pytest

from quotasynch.cli import main
from quotasynch.state import write_last_send
from tests.conftest import NOW, FakeProcess, Machine

FIN_FENETRE = "2026-10-26T12:00:00+02:00"
FIN_SEMAINE = "2026-11-02T12:00:00+02:00"


def poser_releve(
    machine: Machine,
    heure: datetime,
    fenetre: tuple[float, str] | None,
    semaine: tuple[float, str] | None,
) -> None:
    """Écrit une ligne de relevé ; une limite absente s'écrit null, comme `releve` le fait."""
    ligne: dict[str, Any] = {
        "heure": heure.isoformat(),
        "fenetre_pct": None if fenetre is None else fenetre[0],
        "fenetre_fin": None if fenetre is None else fenetre[1],
        "semaine_pct": None if semaine is None else semaine[0],
        "semaine_fin": None if semaine is None else semaine[1],
        "age": 0,
    }
    machine.releves_file.parent.mkdir(parents=True, exist_ok=True)
    machine.releves_file.write_text(json.dumps(ligne) + "\n", encoding="utf-8")


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


def test_status_montre_le_dernier_releve_avec_ses_deux_limites(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    poser_releve(
        machine,
        NOW - timedelta(minutes=3),
        fenetre=(23.6, FIN_FENETRE),
        semaine=(41.2, FIN_SEMAINE),
    )

    assert main(["status"], machine.system) == 0

    sortie = capsys.readouterr().out
    assert sortie.splitlines()[-1] == "dernier relevé : fenêtre 24 %, semaine 41 % (il y a 3 min)"


def test_status_marque_d_un_tiret_la_limite_absente_du_releve(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    poser_releve(machine, NOW, fenetre=None, semaine=(41.2, FIN_SEMAINE))

    assert main(["status"], machine.system) == 0

    assert "dernier relevé : fenêtre –, semaine 41 % (il y a 0 min)" in (capsys.readouterr().out)


def test_status_dit_aucun_releve_sans_fichier(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status"], machine.system) == 0

    assert "dernier relevé : aucun" in capsys.readouterr().out


def test_status_dit_aucun_releve_si_la_seule_ligne_est_illisible(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    machine.releves_file.parent.mkdir(parents=True)
    machine.releves_file.write_text("ligne tronquée {\n", encoding="utf-8")

    assert main(["status"], machine.system) == 0

    assert "dernier relevé : aucun" in capsys.readouterr().out


def test_status_compte_l_age_du_releve_en_minutes_entieres_depuis_l_horloge(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    poser_releve(machine, NOW, fenetre=(23.4, FIN_FENETRE), semaine=(41.2, FIN_SEMAINE))
    sept_minutes_trente_apres = dataclasses.replace(
        machine.system, clock=lambda: NOW + timedelta(minutes=7, seconds=30)
    )

    assert main(["status"], sept_minutes_trente_apres) == 0

    assert "(il y a 7 min)" in capsys.readouterr().out
