"""Les relevés du quota : une ligne JSON par relevé, en ajout seul, tirée de l'instantané."""

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from quotasynch.system import System


@dataclass(frozen=True)
class Limite:
    pct: float
    fin: datetime


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
    heure = system.clock()
    instantane = _lire_instantane(system, heure)
    if instantane is None:
        return
    ecrit, fenetre, semaine = instantane
    if fenetre is None and semaine is None:
        return
    dernier = read_last(system.releves_file())
    if dernier is not None and ecrit <= dernier.ecrit:
        return
    _ajouter(
        system.releves_file(),
        Releve(
            heure=heure,
            fenetre=fenetre,
            semaine=semaine,
            age=math.floor((heure - ecrit).total_seconds()),
        ),
    )


def _lire_instantane(
    system: System, heure: datetime
) -> tuple[datetime, Limite | None, Limite | None] | None:
    """L'écriture de l'instantané et ses limites ; None s'il est absent ou illisible."""
    chemin = system.snapshot_file()
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        ecrit = datetime.fromtimestamp(chemin.stat().st_mtime, tz=heure.tzinfo)
    except (OSError, ValueError):
        return None
    limites = donnees.get("rate_limits") if isinstance(donnees, dict) else None
    if not isinstance(limites, dict):
        return None
    return ecrit, _limite(limites.get("five_hour"), heure), _limite(limites.get("seven_day"), heure)


def _limite(fenetre: Any, heure: datetime) -> Limite | None:
    """Une fenêtre absente ou mal formée compte comme absente."""
    try:
        return Limite(
            pct=float(fenetre["used_percentage"]),
            fin=datetime.fromtimestamp(fenetre["resets_at"], tz=heure.tzinfo),
        )
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None


def read_last(path: Path) -> Releve | None:
    """Le relevé le plus récent ; une ligne illisible est ignorée."""
    try:
        lignes = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for ligne in reversed(lignes):
        try:
            return _parse(ligne)
        except (ValueError, KeyError, TypeError):
            continue
    return None


def _parse(ligne: str) -> Releve:
    donnees = json.loads(ligne)
    heure = datetime.fromisoformat(donnees["heure"])
    if heure.tzinfo is None:
        raise ValueError("heure sans fuseau")
    return Releve(
        heure=heure,
        fenetre=_lire_limite(donnees["fenetre_pct"], donnees["fenetre_fin"]),
        semaine=_lire_limite(donnees["semaine_pct"], donnees["semaine_fin"]),
        age=int(donnees["age"]),
    )


def _lire_limite(pct: Any, fin: Any) -> Limite | None:
    if pct is None:
        return None
    return Limite(pct=float(pct), fin=datetime.fromisoformat(fin))


def _ajouter(path: Path, releve: Releve) -> None:
    fenetre, semaine = releve.fenetre, releve.semaine
    ligne = {
        "heure": releve.heure.isoformat(),
        "fenetre_pct": None if fenetre is None else fenetre.pct,
        "fenetre_fin": None if fenetre is None else fenetre.fin.isoformat(),
        "semaine_pct": None if semaine is None else semaine.pct,
        "semaine_fin": None if semaine is None else semaine.fin.isoformat(),
        "age": releve.age,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(ligne, ensure_ascii=False) + "\n")
