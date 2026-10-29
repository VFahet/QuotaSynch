"""La consommation du quota, tirée des variations que la statusline consigne."""

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from quotasynch import jsonl
from quotasynch.interface import NONE
from quotasynch.system import System

DUREE_FENETRE = timedelta(hours=5)
ECART_DATABLE = timedelta(minutes=30)
FENETRES_AFFICHEES = 50


@dataclass(frozen=True)
class LigneHeure:
    heure: str
    moyenne: str


@dataclass(frozen=True)
class ParHeure:
    lignes: list[LigneHeure]
    premier: str
    dernier: str
    jours: int
    non_date: str

    @property
    def pied(self) -> str:
        """Le pied du tableau des heures : période, nombre de jours, part non datée."""
        jours = "jour" if self.jours == 1 else "jours"
        part = (
            "aucun point de fenêtre"
            if self.non_date == NONE
            else f"{self.non_date} de points non datés"
        )
        return f"Du {self.premier} au {self.dernier} ({self.jours} {jours}) · {part}"


@dataclass(frozen=True)
class LigneFenetre:
    debut: str
    fin: str
    plus_haut: str
    cent: str
    datee: str


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
    variations = _lire(system)
    if not variations:
        return None
    premier = min(v.heure for v in variations).date()
    jours = max(1, (aujourd_hui.date() - premier).days + 1)  # 1 au moins si l'horloge recule
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
        premier=f"{premier:%d/%m}",
        dernier=f"{aujourd_hui:%d/%m}",
        jours=jours,
        non_date=f"{_arrondi(100 * non_dates / total)} %" if total else NONE,
    )


def par_fenetre(system: System) -> list[LigneFenetre]:
    """Les fenêtres, la plus récente d'abord, avec leur plus haut, leur 100 % et leur part datée."""
    variations = _lire(system)
    fenetres = sorted(_fenetres(variations), key=lambda f: f.fin, reverse=True)
    return [_ligne_fenetre(f) for f in fenetres[:FENETRES_AFFICHEES]]


def _ligne_fenetre(fenetre: _Fenetre) -> LigneFenetre:
    points_dates = sum(points for _, points in fenetre.dates)
    total = points_dates + fenetre.non_dates
    return LigneFenetre(
        debut=f"{fenetre.fin - DUREE_FENETRE:%d/%m %H:%M}",
        fin=f"{fenetre.fin:%d/%m %H:%M}",
        plus_haut=f"{_arrondi(fenetre.plus_haut)} %",
        cent=NONE if fenetre.cent is None else f"{fenetre.cent:%H:%M}",
        datee=f"{_arrondi(100 * points_dates / total)} %" if total else NONE,
    )


def _arrondi(valeur: float) -> int:
    """À l'entier le plus proche, moitiés vers le haut."""
    return math.floor(valeur + 0.5)


def _decimale(valeur: float) -> str:
    """À une décimale, moitiés vers le haut comme `_arrondi`, avec une virgule."""
    return f"{_arrondi(valeur * 10) / 10:.1f}".replace(".", ",")


def _lire(system: System) -> list[_Variation]:
    def parse(ligne: str) -> _Variation:
        donnees = json.loads(ligne)
        limite = donnees["rate_limits"]["five_hour"]
        return _Variation(
            heure=system.local_time(donnees["heure"]),
            pct=float(limite["used_percentage"]),
            fin=system.local_time(limite["resets_at"]),
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
    observee = fin - DUREE_FENETRE
    dates: list[tuple[datetime, float]] = []
    non_dates = 0.0
    cent: datetime | None = None
    for variation in sorted(variations, key=lambda v: v.heure):
        if variation.pct < plus_haut:
            continue
        if variation.pct > plus_haut:
            points = variation.pct - plus_haut
            if variation.heure - observee <= ECART_DATABLE:
                dates.append((variation.heure, points))
            else:
                non_dates += points
            plus_haut = variation.pct
            if cent is None and plus_haut >= 100:
                cent = variation.heure
        observee = variation.heure
    return _Fenetre(fin, dates, non_dates, plus_haut, cent)
