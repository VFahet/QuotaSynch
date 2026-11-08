"""Le quota de la semaine en points de fenêtre, estimé à partir des variations.

Le total de la semaine est le nombre de points de fenêtre qui valent 100 % de la semaine. Chaque
observation (points de fenêtre cumulés, pourcentage hebdomadaire entier) en donne une fourchette ;
l'intersection des fourchettes de la semaine se resserre à chaque variation.
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from quotasynch import jsonl
from quotasynch.consommation import DUREE_FENETRE
from quotasynch.system import System

DUREE_SEMAINE = timedelta(days=7)
MARGE = 1.0  # un pourcentage entier, arrondi ou tronqué : la valeur réelle est à moins de 1 point
LARGEUR_MAX = 0.10  # demi-largeur maximale de la fourchette, rapportée au total
ESPACE = " "

type _Limite = tuple[float, datetime]


@dataclass(frozen=True)
class Semaine:
    ligne: str


@dataclass(frozen=True)
class _Variation:
    heure: datetime
    fenetre: _Limite | None
    semaine: _Limite | None


@dataclass(frozen=True)
class _Estimation:
    total: float
    marge: float


def estimation(system: System) -> Semaine | None:
    """La ligne de la semaine en cours ; None sans aucune variation."""
    variations = sorted(_lire(system), key=lambda v: v.heure)
    par_semaine = _par_semaine(variations)
    if not par_semaine:
        return None
    fin_courante = max(par_semaine)
    maintenant = system.clock()
    while fin_courante <= maintenant:  # la semaine vient de commencer, sans variation
        fin_courante += DUREE_SEMAINE
    en_cours = par_semaine.get(fin_courante, [])
    pct = next((v.semaine[0] for v in reversed(en_cours) if v.semaine is not None), 0.0)

    mesure = _retenue(_estimer(fin_courante - DUREE_SEMAINE, en_cours)) if en_cours else None
    precedentes = (
        _retenue(_estimer(fin - DUREE_SEMAINE, par_semaine[fin]))
        for fin in sorted(par_semaine, reverse=True)
        if fin < fin_courante
    )
    precedente = next((e for e in precedentes if e is not None), None)

    debut = f"Semaine : {_arrondi(pct)} %"
    if mesure is not None:
        return Semaine(
            f"{debut} — {_points(pct, mesure.total)} "
            f"(± {_marge(mesure.marge)}, mesuré cette semaine)"
        )
    if precedente is not None:
        return Semaine(f"{debut} — {_points(pct, precedente.total)} (semaine précédente)")
    return Semaine(f"{debut} — total inconnu")


def _estimer(debut: datetime, variations: list[_Variation]) -> _Estimation | None:
    """Le total de la semaine ; None si elle n'est pas mesurable (voir la spec, règle 6)."""
    plus_hauts: dict[datetime, float] = {}
    cumules = 0.0
    bas, haut = 0.0, math.inf
    for variation in variations:
        if variation.fenetre is not None:
            pct, fin = variation.fenetre
            if fin - DUREE_FENETRE < debut:
                return None  # fenêtre à cheval sur la remise à zéro : points de la semaine d'avant
            ancien = plus_hauts.get(fin, 0.0)
            plus_hauts[fin] = max(ancien, pct)
            cumules += max(0.0, pct - ancien)
        if variation.semaine is None:
            continue
        semaine = variation.semaine[0]
        if cumules == 0 or semaine == 0:
            continue
        erreur = MARGE * len(plus_hauts)
        bas = max(bas, 100 * (cumules - erreur) / (semaine + MARGE))
        if semaine > MARGE:
            haut = min(haut, 100 * (cumules + erreur) / (semaine - MARGE))
    if bas > haut or math.isinf(haut):
        return None
    return _Estimation(total=(bas + haut) / 2, marge=(haut - bas) / 2)


def _retenue(estimation: _Estimation | None) -> _Estimation | None:
    """L'estimation seulement si sa fourchette est assez étroite."""
    if estimation is None or estimation.marge > LARGEUR_MAX * estimation.total:
        return None
    return estimation


def _par_semaine(variations: list[_Variation]) -> dict[datetime, list[_Variation]]:
    """Les variations groupées par fin de semaine ; une ligne sans semaine suit son heure."""
    fins = {v.semaine[1] for v in variations if v.semaine is not None}
    groupes: dict[datetime, list[_Variation]] = defaultdict(list)
    for variation in variations:
        if variation.semaine is not None:
            groupes[variation.semaine[1]].append(variation)
            continue
        fin = next((f for f in sorted(fins) if f - DUREE_SEMAINE <= variation.heure < f), None)
        if fin is not None:
            groupes[fin].append(variation)
    return groupes


def _lire(system: System) -> list[_Variation]:
    def limite(brut: Any) -> _Limite | None:
        try:
            return float(brut["used_percentage"]), system.local_time(brut["resets_at"])
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            return None

    def parse(ligne: str) -> _Variation:
        donnees = json.loads(ligne)
        limites = donnees["rate_limits"]
        fenetre = limite(limites.get("five_hour"))
        semaine = limite(limites.get("seven_day"))
        if fenetre is None and semaine is None:
            raise ValueError("aucune limite")
        return _Variation(system.local_time(donnees["heure"]), fenetre, semaine)

    return jsonl.read(system.variations_file(), parse)


def _arrondi(valeur: float) -> int:
    """À l'entier le plus proche, moitiés vers le haut."""
    return math.floor(valeur + 0.5)


def _dizaine(valeur: float) -> int:
    return 10 * _arrondi(valeur / 10)


def _marge(valeur: float) -> str:
    """À la dizaine supérieure : arrondie vers le bas, elle se lirait plus précise qu'elle n'est."""
    return _milliers(10 * math.ceil(valeur / 10))


def _points(pct: float, total: float) -> str:
    consomme, sur = _dizaine(pct * total / 100), _dizaine(total)
    return f"≈ {_milliers(consomme)} / {_milliers(sur)} points de fenêtre"


def _milliers(valeur: int) -> str:
    return f"{valeur:,}".replace(",", ESPACE)
