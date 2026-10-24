import subprocess
from datetime import timedelta

import pytest

from quotasynch.cli import main
from quotasynch.state import read_last_send, write_last_send
from tests.conftest import NOW, FakeProcess, Machine


def test_run_envoie_le_message_par_l_abonnement_depuis_un_dossier_neutre(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run"], machine.system)

    assert code == 0
    [(args, kwargs)] = machine.process.calls
    assert args[1:3] == ["-p", "ok"]
    assert args[3:5] == ["--model", "haiku"]
    assert kwargs["cwd"] == machine.data_dir
    assert "ANTHROPIC_API_KEY" not in kwargs["env"]
    assert kwargs["timeout"] < 60
    assert "envoyé" in capsys.readouterr().out


def test_run_enregistre_la_date_du_dernier_envoi(machine: Machine) -> None:
    main(["run"], machine.system)
    assert read_last_send(machine.state_file) == NOW


def test_run_saute_l_ancrage_quand_une_fenetre_est_ouverte(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    ouverte_depuis = NOW - timedelta(hours=4, minutes=59)
    write_last_send(machine.state_file, ouverte_depuis)

    code = main(["run"], machine.system)

    assert code == 0
    assert machine.process.calls == []
    assert read_last_send(machine.state_file) == ouverte_depuis
    assert "saut" in capsys.readouterr().out


def test_run_envoie_quand_la_fenetre_precedente_vient_de_se_fermer(machine: Machine) -> None:
    write_last_send(machine.state_file, NOW - timedelta(hours=5))
    main(["run"], machine.system)
    assert len(machine.process.calls) == 1
    assert read_last_send(machine.state_file) == NOW


@pytest.mark.parametrize(
    "process",
    [
        FakeProcess(returncode=1, stderr="not logged in"),
        FakeProcess(raises=subprocess.TimeoutExpired("claude", 50)),
        FakeProcess(raises=FileNotFoundError()),
    ],
    ids=["code-non-nul", "delai-depasse", "claude-introuvable"],
)
def test_run_en_echec_sort_en_erreur_sans_enregistrer_d_envoi(
    machine: Machine, process: FakeProcess, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["run"], machine.with_process(process))

    assert code == 1
    assert "quotasynch :" in capsys.readouterr().err
    assert not machine.state_file.exists()


def test_run_avec_une_configuration_invalide_sort_en_erreur(
    machine: Machine, capsys: pytest.CaptureFixture[str]
) -> None:
    machine.config_file.parent.mkdir(parents=True)
    machine.config_file.write_text('anchors = ["05:00", "06:00"]\n', encoding="utf-8")

    assert main(["run"], machine.system) == 1
    assert machine.process.calls == []
    assert "5 h" in capsys.readouterr().err
