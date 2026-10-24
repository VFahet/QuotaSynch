from datetime import time
from pathlib import Path

import pytest

from quotasynch.config import Config, ConfigError, load_config


def ecrire(tmp_path: Path, contenu: str) -> Path:
    chemin = tmp_path / "config.toml"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_sans_fichier_les_heures_par_defaut_sont_5h_10h01_15h02(tmp_path: Path) -> None:
    config = load_config(tmp_path / "absent.toml")
    assert config == Config(
        anchors=(time(5, 0), time(10, 1), time(15, 2)),
        model="haiku",
        message="ok",
        wake=True,
    )


def test_le_fichier_remplace_les_valeurs_par_defaut(tmp_path: Path) -> None:
    chemin = ecrire(
        tmp_path,
        'anchors = ["06:30", "12:00"]\nmodel = "sonnet"\nmessage = "salut"\nwake = false\n',
    )
    assert load_config(chemin) == Config(
        anchors=(time(6, 30), time(12, 0)), model="sonnet", message="salut", wake=False
    )


def test_deux_heures_espacees_de_moins_de_5h_sont_refusees(tmp_path: Path) -> None:
    chemin = ecrire(tmp_path, 'anchors = ["05:00", "09:59"]\n')
    with pytest.raises(ConfigError, match="5 h"):
        load_config(chemin)


def test_l_ecart_entre_la_derniere_heure_et_la_premiere_du_lendemain_compte(
    tmp_path: Path,
) -> None:
    chemin = ecrire(tmp_path, 'anchors = ["01:00", "06:00", "11:00", "21:00"]\n')
    with pytest.raises(ConfigError, match="5 h"):
        load_config(chemin)


def test_une_heure_mal_formee_est_refusee(tmp_path: Path) -> None:
    chemin = ecrire(tmp_path, 'anchors = ["25:00"]\n')
    with pytest.raises(ConfigError, match="25:00"):
        load_config(chemin)


def test_un_toml_invalide_est_refuse(tmp_path: Path) -> None:
    chemin = ecrire(tmp_path, "anchors = [")
    with pytest.raises(ConfigError):
        load_config(chemin)


@pytest.mark.parametrize(
    "contenu",
    [
        'anchors = "05:00"\n',
        'anchors = ["05:00:30"]\n',
        "anchors = []\n",
        'wake = "false"\n',
        "model = 3\n",
    ],
    ids=["pas-une-liste", "avec-secondes", "vide", "wake-texte", "model-nombre"],
)
def test_une_configuration_mal_typee_est_refusee(tmp_path: Path, contenu: str) -> None:
    with pytest.raises(ConfigError):
        load_config(ecrire(tmp_path, contenu))
