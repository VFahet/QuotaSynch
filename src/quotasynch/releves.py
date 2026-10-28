"""Les relevés du quota : une ligne JSON par relevé, en ajout seul, tirée de l'instantané."""

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any

from quotasynch import jsonl
from quotasynch.system import System


@dataclass(frozen=True)
class Limite:
    pct: float
    fin: datetime


@dataclass(frozen=True)
class Instantane:
    ecrit: datetime
    fenetre: Limite | None
    semaine: Limite | None


@dataclass(frozen=True)
class Releve:
    heure: datetime
    fenetre: Limite | None
    semaine: Limite | None
    age: int

    @property
    def ecrit(self) -> datetime:
        """L'instant d'écriture de l'instantané relevé : l'heure du relevé moins son âge."""
        return self.heure - timedelta(seconds=self.age)


def releve(system: System) -> None:
    """Ajoute un relevé si l'instantané a une limite et a changé depuis le dernier relevé."""
    instantane = _lire_instantane(system.instantane_file(), system.clock().tzinfo)
    if instantane is None or (instantane.fenetre is None and instantane.semaine is None):
        return
    heure = system.clock()  # lue après l'instantané : son âge n'est jamais négatif
    dernier = read_last(system.releves_file())
    if dernier is not None and instantane.ecrit <= dernier.ecrit:
        return
    age = math.floor((heure - instantane.ecrit).total_seconds())
    jsonl.append(
        system.releves_file(),
        _ligne(Releve(heure, instantane.fenetre, instantane.semaine, age)),
    )


def _lire_instantane(chemin: Path, fuseau: tzinfo | None) -> Instantane | None:
    """L'instantané et ses limites ; None s'il est absent ou illisible."""
    try:
        ecrit = datetime.fromtimestamp(chemin.stat().st_mtime, tz=fuseau)
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    limites = donnees.get("rate_limits") if isinstance(donnees, dict) else None
    if not isinstance(limites, dict):
        return None
    return Instantane(
        ecrit,
        _limite_de_l_instantane(limites.get("five_hour"), fuseau),
        _limite_de_l_instantane(limites.get("seven_day"), fuseau),
    )


def _limite_de_l_instantane(fenetre: Any, fuseau: tzinfo | None) -> Limite | None:
    """Une fenêtre absente ou mal formée compte comme absente."""
    try:
        return Limite(
            pct=float(fenetre["used_percentage"]),
            fin=datetime.fromtimestamp(fenetre["resets_at"], tz=fuseau),
        )
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None


def read_last(path: Path) -> Releve | None:
    """Le relevé le plus récent ; une ligne illisible est ignorée."""
    lignes = jsonl.read(path, _parse, 1)
    return lignes[0] if lignes else None


def _parse(ligne: str) -> Releve:
    donnees = json.loads(ligne)
    heure = datetime.fromisoformat(donnees["heure"])
    if heure.tzinfo is None:
        raise ValueError("heure sans fuseau")
    return Releve(
        heure=heure,
        fenetre=_limite_du_releve(donnees["fenetre_pct"], donnees["fenetre_fin"]),
        semaine=_limite_du_releve(donnees["semaine_pct"], donnees["semaine_fin"]),
        age=int(donnees["age"]),
    )


def _limite_du_releve(pct: Any, fin: Any) -> Limite | None:
    if pct is None:
        return None
    return Limite(pct=float(pct), fin=datetime.fromisoformat(fin))


def _ligne(releve: Releve) -> dict[str, Any]:
    fenetre, semaine = releve.fenetre, releve.semaine
    return {
        "heure": releve.heure.isoformat(),
        "fenetre_pct": None if fenetre is None else fenetre.pct,
        "fenetre_fin": None if fenetre is None else fenetre.fin.isoformat(),
        "semaine_pct": None if semaine is None else semaine.pct,
        "semaine_fin": None if semaine is None else semaine.fin.isoformat(),
        "age": releve.age,
    }
