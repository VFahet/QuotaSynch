# QuotaSynch

Un petit outil Windows qui envoie un message minimal à Claude Code à des heures choisies, pour que les fenêtres de quota de 5 h démarrent à heures fixes. Rien ne tourne en continu : le Planificateur de tâches Windows lance l'outil aux heures d'ancrage, pendant moins d'une minute.

## Utilisation

Prérequis : Windows 10 ou 11, [`uv`](https://docs.astral.sh/uv/), Claude Code installé et connecté à un abonnement.

```
uv run quotasynch install     # crée la tâche planifiée
uv run quotasynch status      # tâche, configuration, dernier envoi
uv run quotasynch uninstall   # supprime la tâche
```

Par défaut, un message part chaque jour à 05:00, 10:01 et 15:02, et le PC est réveillé si Windows le permet. Sinon, l'envoi est rattrapé dès que le PC redevient disponible.

## Configuration

`%APPDATA%\QuotaSynch\config.toml` (facultatif ; relancer `install` après modification) :

```toml
anchors = ["05:00", "10:01", "15:02"]   # HH:MM, espacées d'au moins 5 h
model = "haiku"
message = "ok"
wake = true                              # réveiller le PC aux heures d'ancrage
```

Les envois passent par l'abonnement : `ANTHROPIC_API_KEY` est retirée de l'environnement de l'appel.

## Développement

`uv run poe check` enchaîne formatage, lint, types et tests.

Licence MIT.
