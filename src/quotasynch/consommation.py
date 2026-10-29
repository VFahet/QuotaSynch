"""La consommation du quota, tirée des variations que la statusline consigne."""

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from quotasynch import jsonl
from quotasynch.system import System

NONE = "—"
DUREE_FENETRE = timedelta(hours=5)
ECART_DATABLE = timedelta(minutes=30)


@dataclass(frozen=True)
class LigneHeure:
    heure: str
    moyenne: str


@dataclass(frozen=True)
class ParHeure:
    lignes: list[LigneHeure]
    periode: str
    jours: int
    non_date: str


@dataclass(frozen=True)
class _Variation:
    heure: datetime
    pct: float
    fin: datetime


@dataclass(frozen=True)
class _Fenetre:
    fin: datetime
    dates: list[tuple[datetime, float]]
    non_dates: float
    plus_haut: float
    cent: datetime | None


def par_heure(system: System) -> ParHeure | None:
    """Les points de fenêtre consommés en moyenne par jour, par heure ; None sans variation."""
    aujourd_hui = system.clock()
    variations = _lire(system, aujourd_hui.tzinfo)
    if not variations:
        return None
    premier = min(v.heure for v in variations).date()
    jours = (aujourd_hui.date() - premier).days + 1
    par_heure_du_jour: dict[int, float] = defaultdict(float)
    non_dates = 0.0
    for fenetre in _fenetres(variations):
        for heure, points in fenetre.dates:
            par_heure_du_jour[heure.hour] += points
        non_dates += fenetre.non_dates
    total = sum(par_heure_du_jour.values()) + non_dates
    return ParHeure(
        lignes=[
            LigneHeure(
                f"{h:02d} h",
                _decimale(par_heure_du_jour[h] / jours) if h in par_heure_du_jour else NONE,
            )
            for h in range(24)
        ],
        periode=f"{premier:%d/%m} – {aujourd_hui:%d/%m}",
        jours=jours,
        non_date=f"{math.floor(100 * non_dates / total + 0.5)} %" if total else NONE,
    )


def _decimale(valeur: float) -> str:
    return f"{valeur:.1f}".replace(".", ",")


def _lire(system: System, fuseau: tzinfo | None) -> list[_Variation]:
    def parse(ligne: str) -> _Variation:
        donnees = json.loads(ligne)
        limite = donnees["rate_limits"]["five_hour"]
        return _Variation(
            heure=datetime.fromtimestamp(donnees["heure"], tz=fuseau),
            pct=float(limite["used_percentage"]),
            fin=datetime.fromtimestamp(limite["resets_at"], tz=fuseau),
        )

    return jsonl.read(system.variations_file(), parse)


def _fenetres(variations: list[_Variation]) -> list[_Fenetre]:
    """Les fenêtres, groupées par heure de fin, avec leurs points datés et non datés."""
    groupes: dict[datetime, list[_Variation]] = defaultdict(list)
    for variation in variations:
        groupes[variation.fin].append(variation)
    return [_dater(fin, groupe) for fin, groupe in groupes.items()]


def _dater(fin: datetime, variations: list[_Variation]) -> _Fenetre:
    """Date chaque hausse à l'heure de sa variation si la précédente observation est récente.

    On part de 0 au début de la fenêtre. Une baisse est ignorée (une session inactive renvoie
    un pourcentage ancien) ; une valeur égale au plus haut prolonge l'observation.
    """
    plus_haut = 0.0
    vu = fin - DUREE_FENETRE
    dates: list[tuple[datetime, float]] = []
    non_dates = 0.0
    cent: datetime | None = None
    for variation in sorted(variations, key=lambda v: v.heure):
        if variation.pct < plus_haut:
            continue
        if variation.pct > plus_haut:
            points = variation.pct - plus_haut
            if variation.heure - vu <= ECART_DATABLE:
                dates.append((variation.heure, points))
            else:
                non_dates += points
            plus_haut = variation.pct
            if cent is None and plus_haut >= 100:
                cent = variation.heure
        vu = variation.heure
    return _Fenetre(fin, dates, non_dates, plus_haut, cent)
