import json
import re
from datetime import datetime

from quotasynch.semaine import estimation
from tests.conftest import NOW, Machine

FUSEAU = NOW.tzinfo
NBSP = " "

# NOW est le lundi 26/10 à 10:01 : la semaine en cours va du 26/10 06:00 au 02/11 06:00.
FIN_SEMAINE = datetime(2026, 11, 2, 6, 0, tzinfo=FUSEAU)
FIN_PRECEDENTE = datetime(2026, 10, 26, 6, 0, tzinfo=FUSEAU)


def _a(mois: int, jour: int, heure: int, minute: int = 0) -> datetime:
    return datetime(2026, mois, jour, heure, minute, tzinfo=FUSEAU)


def _ajoute(machine: Machine, ligne: str) -> None:
    machine.variations_file.parent.mkdir(parents=True, exist_ok=True)
    with machine.variations_file.open("a", encoding="utf-8") as fichier:
        fichier.write(ligne + "\n")


def _variation(
    machine: Machine,
    vue: datetime,
    semaine: tuple[float, datetime] | None,
    fenetre: tuple[float, datetime] | None = None,
) -> None:
    limites = {}
    if fenetre is not None:
        limites["five_hour"] = {"used_percentage": fenetre[0], "resets_at": _ts(fenetre[1])}
    if semaine is not None:
        limites["seven_day"] = {"used_percentage": semaine[0], "resets_at": _ts(semaine[1])}
    _ajoute(machine, json.dumps({"heure": _ts(vue), "rate_limits": limites}))


def _ts(instant: datetime) -> int:
    return int(instant.timestamp())


def _deux_fenetres_pleines(machine: Machine, jour: int, mois: int, fin_semaine: datetime) -> None:
    """Deux fenêtres pleines (200 points), le hebdomadaire à 17 % : 1 181 ± 81 points."""
    fin_a, fin_b = _a(mois, jour, 11), _a(mois, jour, 16)
    _variation(machine, _a(mois, jour, 6, 30), (3, fin_semaine), (40, fin_a))
    _variation(machine, _a(mois, jour, 8), (8, fin_semaine), (100, fin_a))
    _variation(machine, _a(mois, jour, 12), (17, fin_semaine), (100, fin_b))


def _ligne(machine: Machine) -> str:
    vue = estimation(machine.system)
    assert vue is not None
    return vue.ligne


def _marge(ligne: str) -> int:
    trouve = re.search(r"± (\d+)", ligne)
    assert trouve is not None
    return int(trouve.group(1))


def test_aucune_variation_ne_donne_rien(machine: Machine) -> None:
    assert estimation(machine.system) is None


def test_une_semaine_mesuree_donne_le_total_et_sa_marge(machine: Machine) -> None:
    _deux_fenetres_pleines(machine, 26, 10, FIN_SEMAINE)

    assert _ligne(machine) == (
        f"Semaine : 17 % — ≈ 200 / 1{NBSP}180 points de fenêtre (± 90, mesuré cette semaine)"
    )


def test_le_total_se_resserre_quand_une_variation_arrive(machine: Machine) -> None:
    _deux_fenetres_pleines(machine, 26, 10, FIN_SEMAINE)
    avant = _marge(_ligne(machine))

    _variation(machine, _a(10, 26, 17), (25, FIN_SEMAINE), (100, _a(10, 26, 21)))

    assert _marge(_ligne(machine)) == 70 < avant


def test_une_variation_sans_fenetre_apporte_son_pourcentage_sans_points(machine: Machine) -> None:
    _deux_fenetres_pleines(machine, 26, 10, FIN_SEMAINE)

    _variation(machine, _a(10, 26, 20), (18, FIN_SEMAINE))

    assert _ligne(machine) == (
        f"Semaine : 18 % — ≈ 210 / 1{NBSP}140 points de fenêtre (± 50, mesuré cette semaine)"
    )


def test_une_baisse_une_ligne_illisible_ou_sans_limite_ne_changent_rien(machine: Machine) -> None:
    _deux_fenetres_pleines(machine, 26, 10, FIN_SEMAINE)
    attendu = _ligne(machine)

    _variation(machine, _a(10, 26, 13), (17, FIN_SEMAINE), (30, _a(10, 26, 11)))  # baisse
    _ajoute(machine, "{illisible")
    _ajoute(machine, json.dumps({"heure": _ts(_a(10, 26, 13)), "rate_limits": {}}))

    assert _ligne(machine) == attendu


def test_une_premiere_fenetre_seule_est_trop_large_et_le_total_reste_inconnu(
    machine: Machine,
) -> None:
    _variation(machine, _a(10, 26, 7), (7, FIN_SEMAINE), (83, _a(10, 26, 11)))  # 1 212 ± 187

    assert _ligne(machine) == "Semaine : 7 % — total inconnu"


def test_une_fourchette_trop_large_reprend_le_total_de_la_semaine_precedente(
    machine: Machine,
) -> None:
    _deux_fenetres_pleines(machine, 20, 10, FIN_PRECEDENTE)
    _variation(machine, _a(10, 26, 7), (7, FIN_SEMAINE), (83, _a(10, 26, 11)))

    assert _ligne(machine) == (
        f"Semaine : 7 % — ≈ 80 / 1{NBSP}180 points de fenêtre (semaine précédente)"
    )


def test_une_semaine_sans_variation_repart_de_zero_avec_le_total_precedent(
    machine: Machine,
) -> None:
    _deux_fenetres_pleines(machine, 20, 10, FIN_PRECEDENTE)  # finie avant NOW

    assert _ligne(machine) == (
        f"Semaine : 0 % — ≈ 0 / 1{NBSP}180 points de fenêtre (semaine précédente)"
    )


def test_une_fenetre_a_cheval_sur_la_remise_a_zero_rend_la_semaine_non_mesurable(
    machine: Machine,
) -> None:
    fin_b = _a(10, 26, 16)
    _variation(machine, _a(10, 26, 7), (8, FIN_SEMAINE), (100, _a(10, 26, 8)))  # début 03:00
    _variation(machine, _a(10, 26, 12), (17, FIN_SEMAINE), (100, fin_b))

    assert _ligne(machine) == "Semaine : 17 % — total inconnu"


def test_une_intersection_vide_rend_la_semaine_non_mesurable(machine: Machine) -> None:
    _variation(machine, _a(10, 26, 8), (5, FIN_SEMAINE), (100, _a(10, 26, 11)))  # T ≥ 1 650
    _variation(machine, _a(10, 26, 12), (17, FIN_SEMAINE), (100, _a(10, 26, 16)))  # T ≤ 1 262

    assert _ligne(machine) == "Semaine : 17 % — total inconnu"


def test_une_ligne_sans_semaine_est_rattachee_a_la_semaine_de_son_heure(machine: Machine) -> None:
    _variation(machine, _a(10, 26, 6, 30), (3, FIN_SEMAINE), (40, _a(10, 26, 11)))
    _variation(machine, _a(10, 26, 8), (8, FIN_SEMAINE), (100, _a(10, 26, 11)))
    _variation(machine, _a(10, 26, 12), None, (100, _a(10, 26, 16)))  # sans hebdomadaire
    _variation(machine, _a(10, 26, 12, 5), (17, FIN_SEMAINE))

    assert "mesuré cette semaine" in _ligne(machine)
