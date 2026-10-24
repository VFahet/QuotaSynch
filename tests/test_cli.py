import pytest

from quotasynch.cli import main


def test_la_commande_exige_une_sous_commande() -> None:
    with pytest.raises(SystemExit) as sortie:
        main([])
    assert sortie.value.code == 2
