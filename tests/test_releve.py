import dataclasses
import json
import os
from datetime import datetime, timedelta
from typing import Any

import pytest

from quotasynch.cli import main
from tests.conftest import NOW, Machine

FIN_FENETRE = 1793008800  # 2026-10-26 12:00 à +02:00
FIN_SEMAINE = 1793613600  # 2026-11-02 12:00 à +02:00

LIMITES = {
    "five_hour": {"used_percentage": 23.5, "resets_at": FIN_FENETRE},
    "seven_day": {"used_percentage": 41.2, "resets_at": FIN_SEMAINE},
}


def poser_instantane(machine: Machine, donnees: Any, ecrit: datetime) -> None:
    """Écrit l'instantané et fixe sa date de modification."""
    machine.instantane_file.parent.mkdir(parents=True, exist_ok=True)
    machine.instantane_file.write_text(json.dumps(donnees), encoding="utf-8")
    epoch = ecrit.timestamp()
    os.utime(machine.instantane_file, (epoch, epoch))


def test_releve_ajoute_une_ligne_avec_les_deux_limites_et_l_age(machine: Machine) -> None:
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))

    code = main(["releve"], machine.system)

    assert code == 0
    assert machine.releves() == [
        {
            "heure": "2026-10-26T10:01:00+02:00",
            "fenetre_pct": 23.5,
            "fenetre_fin": "2026-10-26T12:00:00+02:00",
            "semaine_pct": 41.2,
            "semaine_fin": "2026-11-02T12:00:00+02:00",
            "age": 90,
        }
    ]


def test_releve_met_null_pour_la_limite_absente_de_l_instantane(machine: Machine) -> None:
    poser_instantane(
        machine,
        {"rate_limits": {"five_hour": LIMITES["five_hour"]}},
        NOW - timedelta(seconds=90),
    )

    assert main(["releve"], machine.system) == 0

    [ligne] = machine.releves()
    assert ligne["fenetre_pct"] == 23.5
    assert ligne["fenetre_fin"] == "2026-10-26T12:00:00+02:00"
    assert ligne["semaine_pct"] is None
    assert ligne["semaine_fin"] is None


def test_releve_ne_double_pas_un_instantane_deja_releve(machine: Machine) -> None:
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))
    main(["releve"], machine.system)
    quinze_minutes_apres = dataclasses.replace(
        machine.system, clock=lambda: NOW + timedelta(minutes=15)
    )

    assert main(["releve"], quinze_minutes_apres) == 0

    assert len(machine.releves()) == 1


def test_releve_ignore_une_ligne_illisible_du_fichier_des_releves(machine: Machine) -> None:
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))
    main(["releve"], machine.system)
    with machine.releves_file.open("a", encoding="utf-8") as fichier:
        fichier.write("ligne tronquée {\n")
    quinze_minutes_apres = dataclasses.replace(
        machine.system, clock=lambda: NOW + timedelta(minutes=15)
    )

    assert main(["releve"], quinze_minutes_apres) == 0

    assert len(machine.releves_file.read_text(encoding="utf-8").splitlines()) == 2


def test_releve_ajoute_une_ligne_quand_l_instantane_est_plus_recent_que_le_dernier_releve(
    machine: Machine,
) -> None:
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))
    main(["releve"], machine.system)
    poser_instantane(
        machine,
        {"rate_limits": {"five_hour": {"used_percentage": 30.0, "resets_at": FIN_FENETRE}}},
        NOW + timedelta(minutes=5),
    )
    quinze_minutes_apres = dataclasses.replace(
        machine.system, clock=lambda: NOW + timedelta(minutes=15)
    )

    main(["releve"], quinze_minutes_apres)

    deuxieme = machine.releves()[1]
    assert deuxieme["heure"] == "2026-10-26T10:16:00+02:00"
    assert deuxieme["fenetre_pct"] == 30.0
    assert deuxieme["age"] == 600


def test_releve_en_echec_d_ecriture_sort_en_erreur_avec_un_avertissement(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))
    machine.releves_file.mkdir(parents=True)  # le fichier des relevés ne peut pas s'ouvrir

    assert main(["releve"], machine.system) == 1
    assert "quotasynch :" in capsys.readouterr().err


def test_releve_ne_lit_pas_la_configuration(machine: Machine) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text("ceci n'est pas une configuration valide", encoding="utf-8")
    poser_instantane(machine, {"rate_limits": LIMITES}, NOW - timedelta(seconds=90))

    assert main(["releve"], machine.system) == 0

    assert len(machine.releves()) == 1


def test_releve_sans_instantane_ne_fait_rien(machine: Machine) -> None:
    assert main(["releve"], machine.system) == 0

    assert machine.releves() == []
    assert not machine.releves_file.exists()


def test_releve_avec_un_instantane_illisible_ne_fait_rien(machine: Machine) -> None:
    machine.instantane_file.parent.mkdir(parents=True)
    machine.instantane_file.write_text('{"rate_limits": ', encoding="utf-8")

    assert main(["releve"], machine.system) == 0

    assert machine.releves() == []


def test_releve_avec_un_instantane_qui_n_est_pas_un_objet_ne_fait_rien(machine: Machine) -> None:
    poser_instantane(machine, ["rate_limits"], NOW - timedelta(seconds=90))

    assert main(["releve"], machine.system) == 0

    assert machine.releves() == []


def test_releve_traite_une_fenetre_mal_formee_comme_absente(machine: Machine) -> None:
    donnees = {
        "rate_limits": {
            "five_hour": {"used_percentage": "beaucoup", "resets_at": FIN_FENETRE},
            "seven_day": LIMITES["seven_day"],
        }
    }
    poser_instantane(machine, donnees, NOW - timedelta(seconds=90))

    assert main(["releve"], machine.system) == 0

    [ligne] = machine.releves()
    assert ligne["fenetre_pct"] is None
    assert ligne["semaine_pct"] == 41.2


def test_releve_sans_aucune_limite_ne_fait_rien(machine: Machine) -> None:
    poser_instantane(machine, {"rate_limits": {}}, NOW - timedelta(seconds=90))

    assert main(["releve"], machine.system) == 0

    assert machine.releves() == []
