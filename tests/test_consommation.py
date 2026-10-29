import json
from datetime import datetime, timedelta

from quotasynch.consommation import LigneFenetre, par_fenetre, par_heure
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
    assert vue.pied == "Du 25/10 au 26/10 (2 jours) · 44 % de points non datés"  # 18 sur 41


def test_sans_aucun_point_la_part_non_datee_est_un_tiret(machine: Machine) -> None:
    _variation(machine, _a(26, 9, 0), 0, _a(26, 12, 0))

    vue = par_heure(machine.system)

    assert vue is not None
    assert {ligne.moyenne for ligne in vue.lignes} == {"—"}
    assert vue.pied == "Du 26/10 au 26/10 (1 jour) · aucun point de fenêtre"


def test_une_hausse_a_30_min_pile_est_datee_meme_ecrite_dans_le_desordre(
    machine: Machine,
) -> None:
    fin = _a(26, 12, 0)
    _variation(machine, _a(26, 8, 0), 9, fin)  # écrite avant la précédente
    _variation(machine, _a(26, 7, 30), 4, fin)  # 4 datés à 7 h, 30 min pile après le début

    vue = par_heure(machine.system)

    assert vue is not None
    moyennes = {ligne.heure: ligne.moyenne for ligne in vue.lignes if ligne.moyenne != "—"}
    assert moyennes == {"07 h": "4,0", "08 h": "5,0"}  # 5 datés à 8 h, 30 min pile après 07:30


def test_fenetres_les_plus_recentes_d_abord_avec_plus_haut_heure_du_100_et_part_datee(
    machine: Machine,
) -> None:
    # Fenêtre du 25/10 02:00–07:00 : 100 % atteint à 02:20, 20 min après le début.
    _variation(machine, _a(25, 2, 20), 100, _a(25, 7, 0))  # 100 datés
    # Fenêtre du 26/10 07:00–12:00 : ni 100 %, ni tout daté.
    fin_26 = _a(26, 12, 0)
    _variation(machine, _a(26, 7, 10), 5, fin_26)  # 5 datés
    _variation(machine, _a(26, 8, 15), 12, fin_26)  # 7 non datés, 65 min après 07:10
    _variation(machine, _a(26, 9, 0), 20, fin_26)  # 8 non datés, 45 min après 08:15
    _variation(machine, _a(26, 9, 10), 26, fin_26)  # 6 datés

    lignes = par_fenetre(machine.system)

    assert lignes == [
        LigneFenetre("26/10 07:00", "26/10 12:00", "26 %", "—", "42 %"),  # 11 datés sur 26
        LigneFenetre("25/10 02:00", "25/10 07:00", "100 %", "02:20", "100 %"),
    ]


def test_une_fenetre_sans_point_a_une_part_datee_en_tiret(machine: Machine) -> None:
    _variation(machine, _a(26, 9, 0), 0, _a(26, 12, 0))

    assert par_fenetre(machine.system) == [
        LigneFenetre("26/10 07:00", "26/10 12:00", "0 %", "—", "—"),
    ]


def test_aucune_variation_ne_donne_aucune_fenetre(machine: Machine) -> None:
    assert par_fenetre(machine.system) == []


def test_au_plus_50_fenetres_les_plus_recentes(machine: Machine) -> None:
    debut = datetime(2026, 9, 1, tzinfo=FUSEAU)
    for i in range(51):
        fin = debut + timedelta(hours=5 * (i + 1))
        _variation(machine, fin - timedelta(hours=4), 1, fin)

    lignes = par_fenetre(machine.system)

    assert len(lignes) == 50
    assert (lignes[0].fin, lignes[-1].fin) == ("11/09 15:00", "01/09 10:00")
