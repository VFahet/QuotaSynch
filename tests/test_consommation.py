import json
from datetime import datetime

from quotasynch.consommation import par_heure
from tests.conftest import NOW, Machine

FUSEAU = NOW.tzinfo


def _a(jour: int, heure: int, minute: int) -> datetime:
    return datetime(2026, 10, jour, heure, minute, tzinfo=FUSEAU)


def _ajoute(machine: Machine, ligne: str) -> None:
    machine.variations_file.parent.mkdir(parents=True, exist_ok=True)
    with machine.variations_file.open("a", encoding="utf-8") as fichier:
        fichier.write(ligne + "\n")


def _variation(machine: Machine, vue: datetime, pct: float, fin: datetime) -> None:
    limite = {"used_percentage": pct, "resets_at": int(fin.timestamp())}
    ligne = {"heure": int(vue.timestamp()), "rate_limits": {"five_hour": limite}}
    _ajoute(machine, json.dumps(ligne))


def test_aucune_variation_ne_donne_rien(machine: Machine) -> None:
    assert par_heure(machine.system) is None


def test_seule_une_hausse_vue_dans_les_30_min_de_l_observation_precedente_est_datee(
    machine: Machine,
) -> None:
    # Fenêtre du 25/10 02:00–07:00 : le premier pourcentage arrive 1 h après le début.
    fin_25 = _a(25, 7, 0)
    _variation(machine, _a(25, 3, 0), 10, fin_25)  # 10 non datés
    _variation(machine, _a(25, 3, 20), 15, fin_25)  # 5 datés à 3 h
    # Fenêtre du 26/10 07:00–12:00.
    fin_26 = _a(26, 12, 0)
    _variation(machine, _a(26, 7, 10), 5, fin_26)  # 5 datés à 7 h, 10 min après le début
    _variation(machine, _a(26, 7, 50), 5, fin_26)  # égale : prolonge l'observation
    _variation(machine, _a(26, 8, 15), 12, fin_26)  # 7 datés à 8 h, 25 min après 07:50
    _variation(machine, _a(26, 8, 40), 3, fin_26)  # baisse ignorée, ne prolonge rien
    _ajoute(machine, "{illisible")
    _ajoute(machine, json.dumps({"heure": int(_a(26, 8, 50).timestamp()), "rate_limits": {}}))
    _variation(machine, _a(26, 9, 0), 20, fin_26)  # 8 non datés, 45 min après 08:15
    _variation(machine, _a(26, 9, 10), 26, fin_26)  # 6 datés à 9 h

    vue = par_heure(machine.system)

    assert vue is not None
    assert [ligne.heure for ligne in vue.lignes] == [f"{h:02d} h" for h in range(24)]
    moyennes = {ligne.heure: ligne.moyenne for ligne in vue.lignes if ligne.moyenne != "—"}
    assert moyennes == {"03 h": "2,5", "07 h": "2,5", "08 h": "3,5", "09 h": "3,0"}
    assert (vue.periode, vue.jours) == ("25/10 – 26/10", 2)
    assert vue.non_date == "44 %"  # 18 non datés sur 41 points


def test_sans_aucun_point_la_part_non_datee_est_un_tiret(machine: Machine) -> None:
    _variation(machine, _a(26, 9, 0), 0, _a(26, 12, 0))

    vue = par_heure(machine.system)

    assert vue is not None
    assert {ligne.moyenne for ligne in vue.lignes} == {"—"}
    assert (vue.periode, vue.jours, vue.non_date) == ("26/10 – 26/10", 1, "—")
